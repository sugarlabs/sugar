#include <stdio.h>

#include <nsStringAPI.h>
#include <nsCExternalHandlerService.h>
#include <nsIMIMEInfo.h>
#include <nsIURL.h>
#include <nsIFile.h>

#include "sugar-browser-chandler.h"

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
	SugarBrowserChandler *browser_chandler;
	nsresult rv;
	nsCString url;
	nsCString mimeType;
	nsString suggested_file_name_utf16;
	nsCString suggested_file_name;
	nsCString tmp_file_name;
	
	NS_ENSURE_TRUE (aLauncher, NS_ERROR_FAILURE);

	nsCOMPtr<nsIMIMEInfo> MIMEInfo;
	aLauncher->GetMIMEInfo (getter_AddRefs(MIMEInfo));
	NS_ENSURE_TRUE (MIMEInfo, NS_ERROR_FAILURE);

	rv = MIMEInfo->GetMIMEType (mimeType);

	nsCOMPtr<nsIURI> uri;
	aLauncher->GetSource (getter_AddRefs(uri));
	NS_ENSURE_TRUE (uri, NS_ERROR_FAILURE);
	
	uri->GetSpec (url);
	
	aLauncher->GetSuggestedFileName (suggested_file_name_utf16);
	NS_UTF16ToCString (suggested_file_name_utf16,
			   NS_CSTRING_ENCODING_UTF8, suggested_file_name);
	
	nsCOMPtr<nsIFile> tmp_file;
	aLauncher->GetTargetFile(getter_AddRefs(tmp_file));
	tmp_file->GetNativeLeafName (tmp_file_name);
                
	browser_chandler = sugar_get_browser_chandler();
	sugar_browser_chandler_handle_content(browser_chandler,
										  url.get(),
										  suggested_file_name.get(),
										  mimeType.get(),
										  tmp_file_name.get());

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

