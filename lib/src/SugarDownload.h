#ifndef SugarDownload_h__
#define SugarDownload_h__

#include <nsCOMPtr.h>
#include <nsIInterfaceRequestor.h>
#include <nsITransfer.h>
#include <nsIWebProgressListener.h>
#include <nsIMIMEInfo.h>
#include <nsIURL.h>
#include <nsILocalFile.h>
#include <nsStringAPI.h>

#define G_SUGARDOWNLOAD_CID							 \
{ /* b1813bbe-6518-11db-967e-00e08161165f */         \
	0xb1813bbe,                                      \
	0x6518,                                          \
	0x11db,                                          \
	{0x96, 0x7e, 0x0, 0xe0, 0x81, 0x61, 0x16, 0x5f} \
}

class GSugarDownload : public nsITransfer
{
public:
    GSugarDownload();
	virtual ~GSugarDownload();
    
	NS_DECL_ISUPPORTS
	NS_DECL_NSIWEBPROGRESSLISTENER
	NS_DECL_NSIWEBPROGRESSLISTENER2
	NS_DECL_NSITRANSFER

protected:
	nsIURI			*mSource;
	nsCString		mTargetFileName;
	nsIMIMEInfo		*mMIMEInfo;
	nsILocalFile	*mTempFile;
};

#endif // SugarDownload_h__
