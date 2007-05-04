#include <config.h>

#include <stdio.h>

#include <gtkmozembed.h>
#include <gtkmozembed_internal.h>
#include <nsIRequest.h>
#include <nsNetUtil.h>
#include <nsISeekableStream.h>
#include <nsIHttpChannel.h>
#include <nsIUploadChannel.h>
#include <nsIWebBrowser.h>
#include <nsISHistory.h>
#include <nsIHistoryEntry.h>
#include <nsISHEntry.h>
#include <nsIInputStream.h>
#include <nsIWebNavigation.h>

#include "GeckoBrowserPersist.h"

GeckoBrowserPersist::GeckoBrowserPersist(SugarBrowser *browser)
    :   mBrowser(browser)
{
}

GeckoBrowserPersist::~GeckoBrowserPersist()
{
}

static nsresult
NewURI(const char *uri, nsIURI **result)
{
    nsresult rv;

    nsCOMPtr<nsIServiceManager> mgr;
    NS_GetServiceManager (getter_AddRefs (mgr));
    NS_ENSURE_TRUE(mgr, FALSE);

    nsCOMPtr<nsIIOService> ioService;
    rv = mgr->GetServiceByContractID ("@mozilla.org/network/io-service;1",
                                      NS_GET_IID (nsIIOService),
                                      getter_AddRefs(ioService));
    NS_ENSURE_SUCCESS(rv, FALSE);

    nsCString cSpec(uri);
    return ioService->NewURI (cSpec, nsnull, nsnull, result);
}

static nsresult
GetPostData(SugarBrowser *browser, nsIInputStream **postData)
{
    nsCOMPtr<nsIWebBrowser> webBrowser;
    gtk_moz_embed_get_nsIWebBrowser(GTK_MOZ_EMBED(browser),
                                    getter_AddRefs(webBrowser));
    NS_ENSURE_TRUE(webBrowser, NS_ERROR_FAILURE);

    nsCOMPtr<nsIWebNavigation> webNav(do_QueryInterface(webBrowser));
    NS_ENSURE_TRUE(webNav, NS_ERROR_FAILURE);

    PRInt32 sindex;

    nsCOMPtr<nsISHistory> sessionHistory;
    webNav->GetSessionHistory(getter_AddRefs(sessionHistory));
    NS_ENSURE_TRUE(sessionHistory, NS_ERROR_FAILURE);

    nsCOMPtr<nsIHistoryEntry> entry;
    sessionHistory->GetIndex(&sindex);
    sessionHistory->GetEntryAtIndex(sindex, PR_FALSE, getter_AddRefs(entry));

    nsCOMPtr<nsISHEntry> shEntry(do_QueryInterface(entry));
    if (shEntry) {
        shEntry->GetPostData(postData);
    }

    return NS_OK;
}

bool
GeckoBrowserPersist::SaveURI(const char *uri, const char *filename)
{
    nsresult rv;

    nsCOMPtr<nsIURI> sourceURI;
    rv = NewURI(uri, getter_AddRefs(sourceURI));
    NS_ENSURE_SUCCESS(rv, FALSE);

    nsCOMPtr<nsILocalFile> destFile = do_CreateInstance("@mozilla.org/file/local;1");
    NS_ENSURE_TRUE(destFile, FALSE);

    destFile->InitWithNativePath(nsCString(filename));

    nsCOMPtr<nsIInputStream> postData;
    GetPostData(mBrowser, getter_AddRefs(postData));
    
    nsCOMPtr<nsIChannel> inputChannel;
    rv = NS_NewChannel(getter_AddRefs(inputChannel), sourceURI,
            nsnull, nsnull, nsnull, nsIRequest::LOAD_NORMAL);
    NS_ENSURE_SUCCESS(rv, FALSE);
    
    nsCOMPtr<nsIHttpChannel> httpChannel(do_QueryInterface(inputChannel));
    if (httpChannel) {
        nsCOMPtr<nsISeekableStream> stream(do_QueryInterface(postData));
        if (stream)
        {
            // Rewind the postdata stream
            stream->Seek(nsISeekableStream::NS_SEEK_SET, 0);
            nsCOMPtr<nsIUploadChannel> uploadChannel(do_QueryInterface(httpChannel));
            NS_ASSERTION(uploadChannel, "http must support nsIUploadChannel");
            // Attach the postdata to the http channel
            uploadChannel->SetUploadStream(postData, EmptyCString(), -1);
        }
    }
    
    nsCOMPtr<nsIInputStream> stream;
    rv = inputChannel->Open(getter_AddRefs(stream));
    NS_ENSURE_SUCCESS(rv, FALSE);
    
    nsCOMPtr<nsIFileOutputStream> fileOutputStream =
        do_CreateInstance(NS_LOCALFILEOUTPUTSTREAM_CONTRACTID, &rv);
    NS_ENSURE_SUCCESS(rv, FALSE);
    
    rv = fileOutputStream->Init(destFile, -1, -1, 0);
    NS_ENSURE_SUCCESS(rv, FALSE);

    // Read data from the input and write to the output
    char buffer[8192];
    PRUint32 bytesRead;
    PRUint32 bytesRemaining;
    PRBool cancel = PR_FALSE;
    PRBool readError;
            
    rv = stream->Available(&bytesRemaining);
    NS_ENSURE_SUCCESS(rv, FALSE);
    
    while (!cancel && bytesRemaining)
    {
        readError = PR_TRUE;
        rv = stream->Read(buffer, PR_MIN(sizeof(buffer), bytesRemaining), &bytesRead);
        if (NS_SUCCEEDED(rv))
        {
            readError = PR_FALSE;
            // Write out the data until something goes wrong, or, it is
            // all written.  We loop because for some errors (e.g., disk
            // full), we get NS_OK with some bytes written, then an error.
            // So, we want to write again in that case to get the actual
            // error code.
            const char *bufPtr = buffer; // Where to write from.
            while (NS_SUCCEEDED(rv) && bytesRead)
            {
                PRUint32 bytesWritten = 0;
                rv = fileOutputStream->Write(bufPtr, bytesRead, &bytesWritten);
                if (NS_SUCCEEDED(rv))
                {
                    bytesRead -= bytesWritten;
                    bufPtr += bytesWritten;
                    bytesRemaining -= bytesWritten;
                    // Force an error if (for some reason) we get NS_OK but
                    // no bytes written.
                    if (!bytesWritten)
                    {
                        rv = NS_ERROR_FAILURE;
                        cancel = PR_TRUE;
                    }
                }
                else
                {
                    // Disaster - can't write out the bytes - disk full / permission?
                    cancel = PR_TRUE;
                }
            }
        }
        else
        {
            // Disaster - can't read the bytes - broken link / file error?
            cancel = PR_TRUE;
        }
    }
    NS_ENSURE_SUCCESS(rv, FALSE);

    stream->Close();

    return TRUE;
}
