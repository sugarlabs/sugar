#include <nsCExternalHandlerService.h>
#include <nsIFile.h>

#include "GeckoContentHandler.h"

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

