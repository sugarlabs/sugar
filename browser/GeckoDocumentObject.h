#ifndef __GECKO_DOCUMENT_OBJECT_H__
#define __GECKO_DOCUMENT_OBJECT_H__

#include <nsIDOMNode.h>
#include <nsIDOMHTMLImageElement.h>

#include "sugar-browser.h"

class GeckoDocumentObject
{
public:
    GeckoDocumentObject(SugarBrowser *browser, nsIDOMNode *node);
    ~GeckoDocumentObject();

    bool IsImage();
    char *GetImageURI();
    char *GetImageName();
    bool SaveImage(const char *filename);
private:
    SugarBrowser                        *mBrowser;
    nsCOMPtr<nsIDOMNode>                 mNode;
    nsCOMPtr<nsIDOMHTMLImageElement>     mImage;
    nsCString                            mImageURI;
    nsCString                            mImageName;
protected:
    /* additional members */
};

#endif // __GECKO_DOCUMENT_OBJECT_H__
