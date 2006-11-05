#include "sugar-download-manager.h"

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
	SugarDownloadManager *download_manager = sugar_get_download_manager();
		
	if (((aStateFlags & STATE_IS_REQUEST) &&
	     (aStateFlags & STATE_IS_NETWORK) &&
	     (aStateFlags & STATE_START)) ||
	    aStateFlags == STATE_START) {
	
		nsCString url;
		nsCString mimeType;
	
		mMIMEInfo->GetMIMEType(mimeType);
		mSource->GetSpec(url);

		sugar_download_manager_download_started(download_manager,
												url.get(),
												mimeType.get(),
												mTargetFileName.get());

	} else if (((aStateFlags & STATE_IS_REQUEST) &&
	     (aStateFlags & STATE_IS_NETWORK) &&
	     (aStateFlags & STATE_STOP)) ||
	    aStateFlags == STATE_STOP) {
		
		if (NS_SUCCEEDED (aStatus)) {
			sugar_download_manager_download_completed(download_manager,
													  mTargetFileName.get());
		} else {
			sugar_download_manager_download_cancelled(download_manager,
													  mTargetFileName.get());
		}
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
	SugarDownloadManager *download_manager = sugar_get_download_manager();
	PRInt32 percentComplete =
		(PRInt32)(((float)aCurSelfProgress / (float)aMaxSelfProgress) * 100.0);

	sugar_download_manager_update_progress(download_manager,
										   mTargetFileName.get(),
										   percentComplete);

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
