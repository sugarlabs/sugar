#ifdef HAVE_GECKO_1_9

#include <unistd.h>

#include <glib.h>
#include <imgICache.h>
#include <nsComponentManagerUtils.h>
#include <nsCOMPtr.h>
#include <nsIDOMHTMLElement.h>
#include <nsIInterfaceRequestorUtils.h>
#include <nsIIOService.h>
#include <nsILocalFile.h>
#include <nsIMIMEHeaderParam.h>
#include <nsIProperties.h>
#include <nsISupportsPrimitives.h>
#include <nsIURI.h>
#include <nsIURL.h>
#include <nsServiceManagerUtils.h>
#include <nsStringAPI.h>

#include <config.h>
#include "GeckoDocumentObject.h"
#include "GeckoBrowserPersist.h"
                    
GeckoDocumentObject::GeckoDocumentObject(SugarBrowser *browser, nsIDOMNode *node)
    :   mBrowser(browser),
        mNode(node),
        mImage(NULL)
{
}

GeckoDocumentObject::~GeckoDocumentObject()
{
}

bool GeckoDocumentObject::IsImage()
{
    if(mImage) {
        return true;
    }

    nsresult rv;

    PRUint16 type;
    rv = mNode->GetNodeType(&type);
    if(NS_FAILED(rv)) return rv;

    nsCOMPtr<nsIDOMHTMLElement> element = do_QueryInterface(mNode);
    if ((nsIDOMNode::ELEMENT_NODE == type) && element) {
        nsString uTag;
        rv = element->GetLocalName(uTag);
        if(NS_FAILED(rv)) return rv;

        nsCString tag;
        NS_UTF16ToCString (uTag, NS_CSTRING_ENCODING_UTF8, tag);

        if (g_ascii_strcasecmp (tag.get(), "img") == 0) {
            nsCOMPtr <nsIDOMHTMLImageElement> imagePtr;
            imagePtr = do_QueryInterface(mNode, &rv);
            if(NS_FAILED(rv)) return rv;
            
            mImage = imagePtr;

            return true;
        }
    }
    
    return false;
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
FilenameFromContentDisposition(nsCString contentDisposition, nsCString &fileName)
{
    nsresult rv;
    nsCString fallbackCharset;

    nsCOMPtr<nsIMIMEHeaderParam> mimehdrpar =
        do_GetService("@mozilla.org/network/mime-hdrparam;1");
    NS_ENSURE_TRUE(mimehdrpar, NS_ERROR_FAILURE);

    nsString aFileName;
    rv = mimehdrpar->GetParameter (contentDisposition, "filename",
                                   fallbackCharset, PR_TRUE, nsnull,
                                   aFileName);

    if (NS_FAILED(rv) || !fileName.Length()) {
        rv = mimehdrpar->GetParameter (contentDisposition, "name",
                                       fallbackCharset, PR_TRUE, nsnull,
                                       aFileName);
    }

    if (NS_SUCCEEDED(rv) && fileName.Length()) {
        NS_UTF16ToCString (aFileName, NS_CSTRING_ENCODING_UTF8, fileName);
    }

    return NS_OK;
}

char *
GeckoDocumentObject::GetImageName()
{
    if(!IsImage()) {
        return NULL;
    }

    nsresult rv;
    char *imgURIStr = GetImageURI();

    nsCOMPtr<nsIURI> imageURI;
    rv = NewURI(imgURIStr, getter_AddRefs(imageURI));
    NS_ENSURE_SUCCESS(rv, NULL);

    nsCOMPtr<nsIServiceManager> mgr;
    NS_GetServiceManager (getter_AddRefs (mgr));
    NS_ENSURE_TRUE(mgr, NULL);

    nsCOMPtr<imgICache> imgCache;
    rv = mgr->GetServiceByContractID("@mozilla.org/image/cache;1",
                                     NS_GET_IID (imgICache),
                                     getter_AddRefs(imgCache));
    NS_ENSURE_SUCCESS(rv, NULL);

    nsCOMPtr<nsIProperties> imgProperties;
    imgCache->FindEntryProperties(imageURI, getter_AddRefs(imgProperties));
    if (imgProperties) {
        nsCOMPtr<nsISupportsCString> dispositionCString;
        imgProperties->Get("content-disposition",
                           NS_GET_IID(nsISupportsCString),
                           getter_AddRefs(dispositionCString));
        if (dispositionCString) {
            nsCString contentDisposition;
            dispositionCString->GetData(contentDisposition);
            FilenameFromContentDisposition(contentDisposition, mImageName);
        }
    }

    if (!mImageName.Length()) {
        nsCOMPtr<nsIURL> url(do_QueryInterface(imageURI));
        if (url) {
            url->GetFileName(mImageName);
        }
    }

    return mImageName.Length() ? g_strdup(mImageName.get()) : NULL;
}

char *
GeckoDocumentObject::GetImageURI()
{
    if(!IsImage()) {
        return NULL;
    }

    if(!mImageURI.Length()) {
        nsresult rv;
        nsString img;    
        rv = mImage->GetSrc(img);
        if (NS_FAILED(rv)) return NULL;

        NS_UTF16ToCString (img, NS_CSTRING_ENCODING_UTF8, mImageURI);
    }
    return g_strdup(mImageURI.get());
}

bool
GeckoDocumentObject::SaveImage(const char *filename)
{
    GeckoBrowserPersist browserPersist(mBrowser);
    return browserPersist.SaveURI(mImageURI.get(), filename);
}

#endif
