#ifndef __GECKO_DRAG_DROP_HOOKS_H__
#define __GECKO_DRAG_DROP_HOOKS_H__

#include <nsIClipboardDragDropHooks.h>

#include "sugar-browser.h"

class GeckoDragDropHooks : public nsIClipboardDragDropHooks
{
public:
    NS_DECL_ISUPPORTS
    NS_DECL_NSICLIPBOARDDRAGDROPHOOKS

    GeckoDragDropHooks(SugarBrowser *browser);

private:
    ~GeckoDragDropHooks();

    SugarBrowser *mBrowser;

protected:
    /* additional members */
};

#endif // __GECKO_DRAG_DROP_HOOKS_H__
