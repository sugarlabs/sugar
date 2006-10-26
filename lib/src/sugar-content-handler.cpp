#include <stdio.h>

#include <nsStringAPI.h>
#include <nsCExternalHandlerService.h>
#include <nsIMIMEInfo.h>
#include <nsIURL.h>
#include <nsIFile.h>

#include "sugar-browser-chandler.h"
#include "SugarDownload.h"

#include "sugar-content-handler.h"

GSugarContentHandler::GSugarContentHandler()
{

}

GSugarContentHandler::~GSugarContentHandler()
{

}

NS_IMPL_ISUPPORTS1(GSugarContentHandler, nsIHelperAppLauncherDialog)

NS_IMETHODIMP
GSugarContentHandler::Show (nsIHelperAppLauncher *aLauncher,
		       nsISupports *aContext,
		       PRUint32 aReason)
{	
	nsCOMPtr<nsIFile> tmp_file;
	aLauncher->GetTargetFile(getter_AddRefs(tmp_file));
		
	aLauncher->SaveToDisk (tmp_file, PR_FALSE);

	return NS_OK;
}

NS_IMETHODIMP GSugarContentHandler::PromptForSaveToFile(
				    nsIHelperAppLauncher *aLauncher,			    
				    nsISupports *aWindowContext,
				    const PRUnichar *aDefaultFile,
				    const PRUnichar *aSuggestedFileExtension,
				    nsILocalFile **_retval)
{
	return NS_OK;
}

