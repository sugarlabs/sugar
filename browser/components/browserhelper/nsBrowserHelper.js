const Cc = Components.classes;
const Ci = Components.interfaces;
const Cr = Components.results;

const CID = Components.ID("{475e1194-92bc-4e03-92f3-5ad6ccddaca3}");
const CONTRACT_ID = "@laptop.org/browser/browserhelper;1";
const CLASS_NAME = "Browser Helper";

var browser;

function BrowserHelperService() {
}

BrowserHelperService.prototype = {

/* ........ nsIBrowserHelper API .............. */

  getBrowser: function bh_getBrowser(aId) {
    return browser;
  },

  registerBrowser: function bh_registerBrowser(aBrowser, aId) {
    browser = aBrowser;
  },

  unregisterBrowser: function bh_unregisterBrowser(aId) {
  },

  QueryInterface: function(aIID) {
    if (!aIID.equals(Ci.nsISupports) && 
      !aIID.equals(Ci.nsIBrowserHelper)) {
      Components.returnCode = Cr.NS_ERROR_NO_INTERFACE;
      return null;
    }
    
    return this;
  }
;

/* :::::::: Service Registration & Initialization ::::::::::::::: */

/* ........ nsIModule .............. */

const BrowserHelperModule = {

  getClassObject: function(aCompMgr, aCID, aIID) {
    if (aCID.equals(CID)) {
      return BrowserHelperFactory;
    }
    
    Components.returnCode = Cr.NS_ERROR_NOT_REGISTERED;
    return null;
  },

  registerSelf: function(aCompMgr, aFileSpec, aLocation, aType) {
    aCompMgr.QueryInterface(Ci.nsIComponentRegistrar);
    aCompMgr.registerFactoryLocation(CID, CLASS_NAME, CONTRACT_ID, aFileSpec, aLocation, aType);
  },

  unregisterSelf: function(aCompMgr, aLocation, aType) {
    aCompMgr.QueryInterface(Ci.nsIComponentRegistrar);
    aCompMgr.unregisterFactoryLocation(CID, aLocation);
  },

  canUnload: function(aCompMgr) {
    return true;
  }
}

/* ........ nsIFactory .............. */

const BrowserHelperFactory = {

  createInstance: function(aOuter, aIID) {
    if (aOuter != null) {
      Components.returnCode = Cr.NS_ERROR_NO_AGGREGATION;
      return null;
    }
    
    return (new BrowserHelperService()).QueryInterface(aIID);
  },

  lockFactory: function(aLock) { },

  QueryInterface: function(aIID) {
    if (!aIID.equals(Ci.nsISupports) && !aIID.equals(Ci.nsIModule) &&
        !aIID.equals(Ci.nsIFactory) && !aIID.equals(Ci.nsIBrowserHelper)) {
      Components.returnCode = Cr.NS_ERROR_NO_INTERFACE;
      return null;
    }
    
    return this;
  }
};

function NSGetModule(aComMgr, aFileSpec) {
  return BrowserHelperModule;
}
