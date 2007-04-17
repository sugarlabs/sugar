#include <sys/time.h>
#include <time.h>

#include <glib.h>
#include <nsStringAPI.h>
#include <nsCOMPtr.h>
#include <nsITransferable.h>
#include <nsISupportsPrimitives.h>
#include <nsIDOMEventTarget.h>
#include <nsComponentManagerUtils.h>
#include <nsServiceManagerUtils.h>
#include <nsIInterfaceRequestorUtils.h>
#include <nsIDOMMouseEvent.h>

#include <config.h>
#include "GeckoDragDropHooks.h"
#include "GeckoDocumentObject.h"

#define TEXT_URI_LIST   "text/uri-list"
#define TEXT_X_MOZ_URL  "text/x-moz-url"
#define FILE_LOCALHOST  "file://"

//*****************************************************************************
// UriListDataProvider
//*****************************************************************************

class UriListDataProvider : public nsIFlavorDataProvider
{
public:
    UriListDataProvider(GeckoDocumentObject *mDocumentObject);
    virtual ~UriListDataProvider();
    NS_DECL_ISUPPORTS
    NS_DECL_NSIFLAVORDATAPROVIDER
private:
    GeckoDocumentObject *mDocumentObject;
    nsCString            mFilePath;
};

//*****************************************************************************

NS_IMPL_ISUPPORTS1(UriListDataProvider, nsIFlavorDataProvider)                                                   

UriListDataProvider::UriListDataProvider(GeckoDocumentObject *documentObject)
    :   mDocumentObject(documentObject)
{
}

UriListDataProvider::~UriListDataProvider()
{
    if(mFilePath.Length()) {
        remove(mFilePath.get());
    }
    
    delete mDocumentObject;
}

NS_IMETHODIMP
UriListDataProvider::GetFlavorData(nsITransferable *aTransferable,
                                   const char *aFlavor, nsISupports **aData,
                                   PRUint32 *aDataLen)
{
    NS_ENSURE_ARG_POINTER(aData && aDataLen);

    nsresult rv = NS_ERROR_NOT_IMPLEMENTED;
    char *image_name;
    timeval timestamp;

    *aData = nsnull;
    *aDataLen = 0;
    
    if(g_ascii_strcasecmp(aFlavor, TEXT_URI_LIST) != 0) {
        return rv;
    }

    gettimeofday(&timestamp, NULL);
    
    mFilePath.Append(g_get_tmp_dir());
    mFilePath.Append("/");
    mFilePath.AppendInt(timestamp.tv_sec);
    mFilePath.AppendInt(timestamp.tv_usec);

    image_name = mDocumentObject->GetImageName();
    mFilePath.Append(image_name);
    g_free(image_name);

    if(!mDocumentObject->SaveImage(mFilePath.get())) {
        return NS_ERROR_FAILURE;
    }

    nsCString localURI(FILE_LOCALHOST);
    localURI.Append(mFilePath);

    nsString localURI16;
    NS_CStringToUTF16(localURI, NS_CSTRING_ENCODING_UTF8, localURI16);

    nsCOMPtr<nsISupportsString> localURIData(do_CreateInstance(
                "@mozilla.org/supports-string;1", &rv));
    if(NS_FAILED(rv)) return rv;

    rv = localURIData->SetData(localURI16);
    if(NS_FAILED(rv)) return rv;

    CallQueryInterface(localURIData, aData);
    *aDataLen = sizeof(nsISupportsString*);

    // FIXME: Why do we need this? Is there a leak in mozilla?
    this->Release();

    return rv;
}

//*****************************************************************************
// GeckoDragDropHooks
//*****************************************************************************

NS_IMPL_ISUPPORTS1(GeckoDragDropHooks, nsIClipboardDragDropHooks)

GeckoDragDropHooks::GeckoDragDropHooks(SugarBrowser *browser)
    :   mBrowser(browser)
{
}

GeckoDragDropHooks::~GeckoDragDropHooks()
{
}

NS_IMETHODIMP
GeckoDragDropHooks::AllowStartDrag(nsIDOMEvent *event, PRBool *_retval)
{
    return NS_ERROR_NOT_IMPLEMENTED;
}

NS_IMETHODIMP
GeckoDragDropHooks::AllowDrop(nsIDOMEvent *event, nsIDragSession *session,
                              PRBool *_retval)
{
    return NS_ERROR_NOT_IMPLEMENTED;
}

NS_IMETHODIMP
GeckoDragDropHooks::OnCopyOrDrag(nsIDOMEvent *aEvent, nsITransferable *trans,
                                 PRBool *_retval)
{
    nsresult rv;

    *_retval = true;

    nsCOMPtr<nsIDOMMouseEvent> mouseEvent;
    mouseEvent = do_QueryInterface(aEvent, &rv);
    if(NS_FAILED(rv)) return rv;

    nsCOMPtr<nsIDOMEventTarget> eventTarget;
    rv = mouseEvent->GetTarget(getter_AddRefs(eventTarget));
    if(NS_FAILED(rv)) return rv;

    nsCOMPtr<nsIDOMNode> targetNode;
    targetNode = do_QueryInterface(eventTarget, &rv);
    if(NS_FAILED(rv)) return rv;

    GeckoDocumentObject *documentObject = new GeckoDocumentObject(mBrowser,
                                                                  targetNode);
    if(documentObject->IsImage()) {
        rv = trans->RemoveDataFlavor(TEXT_X_MOZ_URL);
        if(NS_FAILED(rv)) return rv;

        rv = trans->AddDataFlavor(TEXT_URI_LIST);
        if(NS_FAILED(rv)) return rv;

        UriListDataProvider *rawPtr = new UriListDataProvider(documentObject);
        nsCOMPtr<nsISupports> dataProvider(do_QueryInterface(rawPtr, &rv));
        if(NS_FAILED(rv)) return rv;

        rv = trans->SetTransferData(TEXT_URI_LIST, dataProvider, 0);
        if(NS_FAILED(rv)) return rv;
    }

    return rv;
}

NS_IMETHODIMP
GeckoDragDropHooks::OnPasteOrDrop(nsIDOMEvent *event, nsITransferable *trans,
                                  PRBool *_retval)
{
    return NS_ERROR_NOT_IMPLEMENTED;
}
