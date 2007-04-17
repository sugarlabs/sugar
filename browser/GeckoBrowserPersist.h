#ifndef __GECKO_BROWSER_PERSIST_H__
#define __GECKO_BROWSER_PERSIST_H__

#include "sugar-browser.h"

class GeckoBrowserPersist
{
public:
    GeckoBrowserPersist(SugarBrowser *browser);
    ~GeckoBrowserPersist();

    bool SaveURI(const char *uri, const char *filename);
private:
    SugarBrowser    *mBrowser;
protected:
    /* additional members */
};

#endif // __GECKO_BROWSER_PERSIST_H__
