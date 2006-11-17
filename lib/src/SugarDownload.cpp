#include "sugar-browser-chandler.h"

#include "SugarDownload.h"

GSugarDownload::GSugarDownload()
{
}

GSugarDownload::~GSugarDownload()
{
}

NS_IMPL_ISUPPORTS3 (GSugarDownload,
		    nsIWebProgressListener,
		    nsIWebProgressListener2,
		    nsITransfer)

NS_IMETHODIMP
GSugarDownload::Init (nsIURI *aSource,
		   nsIURI *aTarget,
		   const nsAString &aDisplayName,
		   nsIMIMEInfo *aMIMEInfo,
		   PRTime aStartTime,
		   nsILocalFile *aTempFile,
		   nsICancelable *aCancelable)
{
	mSource = aSource;
	aTarget->GetPath(mTargetFileName);
	mMIMEInfo = aMIMEInfo;
	mTempFile = aTempFile;

	return NS_OK;
}

NS_IMETHODIMP 
GSugarDownload::OnStateChange (nsIWebProgress *aWebProgress, nsIRequest *aRequest,
			    PRUint32 aStateFlags, nsresult aStatus)
{
	nsCString url;
	nsCString mimeType;
	nsCString targetURI;
	
	if ((((aStateFlags & STATE_IS_REQUEST) &&
	     (aStateFlags & STATE_IS_NETWORK) &&
	     (aStateFlags & STATE_STOP)) ||
	    aStateFlags == STATE_STOP) &&
	    NS_SUCCEEDED (aStatus)) {
	
		mMIMEInfo->GetMIMEType(mimeType);
		mSource->GetSpec(url);

		SugarBrowserChandler *browser_chandler = sugar_get_browser_chandler();
		sugar_browser_chandler_handle_content(browser_chandler,
											  url.get(),
											  mimeType.get(),
											  mTargetFileName.get());
	}
	
	return NS_OK; 
}

NS_IMETHODIMP
GSugarDownload::OnProgressChange (nsIWebProgress *aWebProgress,
			       nsIRequest *aRequest,
			       PRInt32 aCurSelfProgress,
			       PRInt32 aMaxSelfProgress,
			       PRInt32 aCurTotalProgress,
			       PRInt32 aMaxTotalProgress)
{
	return OnProgressChange64 (aWebProgress, aRequest,
				   aCurSelfProgress, aMaxSelfProgress,
				   aCurTotalProgress, aMaxTotalProgress);
}

NS_IMETHODIMP
GSugarDownload::OnProgressChange64 (nsIWebProgress *aWebProgress,
				 nsIRequest *aRequest,
				 PRInt64 aCurSelfProgress,
				 PRInt64 aMaxSelfProgress,
				 PRInt64 aCurTotalProgress,
				 PRInt64 aMaxTotalProgress)
{
	return NS_OK;
}

NS_IMETHODIMP
GSugarDownload::OnLocationChange (nsIWebProgress *aWebProgress, nsIRequest *aRequest, nsIURI *location)
{
	return NS_OK;
}

NS_IMETHODIMP 
GSugarDownload::OnStatusChange (nsIWebProgress *aWebProgress, nsIRequest *aRequest,
			     nsresult aStatus, const PRUnichar *aMessage)
{
	return NS_OK;
}

NS_IMETHODIMP 
GSugarDownload::OnSecurityChange (nsIWebProgress *aWebProgress, nsIRequest *aRequest, PRUint32 state)
{
	return NS_OK;
}
