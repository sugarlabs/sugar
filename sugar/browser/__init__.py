"""Sugar's web-browser activity

XUL Runner and gtkmozembed and is produced by the PyGTK
.defs system.
"""

try:
    from sugar.browser._sugarbrowser import startup, shutdown
    from sugar.browser import _sugarbrowser
except ImportError:
    from sugar import ltihooks
    from sugar.browser._sugarbrowser import startup, shutdown
    from sugar.browser import _sugarbrowser

class Browser(_sugarbrowser.Browser):
    def __init__(self):
        _sugarbrowser.Browser.__init__(self)

    def get_browser(self):
        from xpcom import components
        cls = components.classes["@laptop.org/browser/browserhelper;1"]
        browser_helper = cls.getService(components.interfaces.nsIBrowserHelper)
        print self.get_instance_id()
        return browser_helper.getBrowser(self.get_instance_id())
        
    def get_document(self):
        return self.browser.contentDOMWindow.document
    
    document = property(get_document)
    browser = property(get_browser)
