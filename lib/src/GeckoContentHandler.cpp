#include <nsCExternalHandlerService.h>
#include <nsIFile.h>
#include <nsIFactory.h>

#include "GeckoContentHandler.h"

class GeckoContentHandler : public nsIHelperAppLauncherDialog
{
public:
    NS_DECL_ISUPPORTS
    NS_DECL_NSIHELPERAPPLAUNCHERDIALOG

    GeckoContentHandler();
    virtual ~GeckoContentHandler();
};

GeckoContentHandler::GeckoContentHandler()
{

}

GeckoContentHandler::~GeckoContentHandler()
{

}

NS_IMPL_ISUPPORTS1(GeckoContentHandler, nsIHelperAppLauncherDialog)

NS_IMETHODIMP
GeckoContentHandler::Show (nsIHelperAppLauncher *aLauncher,
						   nsISupports *aContext,
						   PRUint32 aReason)
{	
	nsCOMPtr<nsIFile> tmpFile;
	aLauncher->GetTargetFile(getter_AddRefs(tmpFile));
		
	aLauncher->SaveToDisk (tmpFile, PR_FALSE);

	return NS_OK;
}

NS_IMETHODIMP
GeckoContentHandler::PromptForSaveToFile (nsIHelperAppLauncher *aLauncher,			    
										  nsISupports *aWindowContext,
										  const PRUnichar *aDefaultFile,
										  const PRUnichar *aSuggestedFileExtension,
										  nsILocalFile **_retval)
{
	return NS_OK;
}

//*****************************************************************************
// GeckoContentHandlerFactory
//*****************************************************************************

class GeckoContentHandlerFactory : public nsIFactory {
public:
  NS_DECL_ISUPPORTS
  NS_DECL_NSIFACTORY

  GeckoContentHandlerFactory();
  virtual ~GeckoContentHandlerFactory();
};

//*****************************************************************************

NS_IMPL_ISUPPORTS1(GeckoContentHandlerFactory, nsIFactory)

GeckoContentHandlerFactory::GeckoContentHandlerFactory() {
}

GeckoContentHandlerFactory::~GeckoContentHandlerFactory() {
}

NS_IMETHODIMP
GeckoContentHandlerFactory::CreateInstance(nsISupports *aOuter,
                                           const nsIID & aIID,
                                           void **aResult)
{
    NS_ENSURE_ARG_POINTER(aResult);

    *aResult = NULL;
    GeckoContentHandler *inst = new GeckoContentHandler;
    if (!inst)
        return NS_ERROR_OUT_OF_MEMORY;

    nsresult rv = inst->QueryInterface(aIID, aResult);
    if (rv != NS_OK) {
        // We didn't get the right interface, so clean up
        delete inst;
    }

    return rv;
}

NS_IMETHODIMP
GeckoContentHandlerFactory::LockFactory(PRBool lock)
{
    return NS_OK;
}

//*****************************************************************************

nsresult
NS_NewGeckoContentHandlerFactory(nsIFactory** aFactory)
{
    NS_ENSURE_ARG_POINTER(aFactory);
    *aFactory = nsnull;

    GeckoContentHandlerFactory *result = new GeckoContentHandlerFactory;
    if (!result)
        return NS_ERROR_OUT_OF_MEMORY;

    NS_ADDREF(result);
    *aFactory = result;

    return NS_OK;
}
