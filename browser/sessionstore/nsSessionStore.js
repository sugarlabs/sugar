/* ***** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1/GPL 2.0/LGPL 2.1
 *
 * The contents of this file are subject to the Mozilla Public License Version
 * 1.1 (the "License"); you may not use this file except in compliance with
 * the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 *
 * Software distributed under the License is distributed on an "AS IS" basis,
 * WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
 * for the specific language governing rights and limitations under the
 * License.
 *
 * The Original Code is the nsSessionStore component.
 *
 * The Initial Developer of the Original Code is
 * Simon Bünzli <zeniko@gmail.com>
 * Portions created by the Initial Developer are Copyright (C) 2006
 * the Initial Developer. All Rights Reserved.
 *
 * Contributor(s):
 *   Dietrich Ayala <autonome@gmail.com>
 *
 * Alternatively, the contents of this file may be used under the terms of
 * either the GNU General Public License Version 2 or later (the "GPL"), or
 * the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
 * in which case the provisions of the GPL or the LGPL are applicable instead
 * of those above. If you wish to allow use of your version of this file only
 * under the terms of either the GPL or the LGPL, and not to allow others to
 * use your version of this file under the terms of the MPL, indicate your
 * decision by deleting the provisions above and replace them with the notice
 * and other provisions required by the GPL or the LGPL. If you do not delete
 * the provisions above, a recipient may use your version of this file under
 * the terms of any one of the MPL, the GPL or the LGPL.
 *
 * ***** END LICENSE BLOCK ***** */

/*
 * Heavily adapted to xulrunner for the OLPC from the firefox code in
 * http://lxr.mozilla.org/seamonkey/source/browser/components/sessionstore.
 *
 * May 2007 Tomeu Vizoso
 */

/**
 * Session Storage and Restoration
 * 
 * Overview
 * This service keeps track of a user's session, storing the various bits
 * required to return the browser to it's current state. The relevant data is 
 * stored in memory, and is periodically saved to disk in a file in the 
 * profile directory. The service is started at first window load, in
 * delayedStartup, and will restore the session from the data received from
 * the nsSessionStartup service.
 */

/* :::::::: Constants and Helpers ::::::::::::::: */

const Cc = Components.classes;
const Ci = Components.interfaces;
const Cr = Components.results;

const CID = Components.ID("{5280606b-2510-4fe0-97ef-9b5a22eafe6b}");
const CONTRACT_ID = "@mozilla.org/browser/sessionstore;1";
const CLASS_NAME = "Browser Session Store Service";

// sandbox to evaluate JavaScript code from non-trustable sources
var EVAL_SANDBOX = new Components.utils.Sandbox("about:blank");

function debug(aMsg) {
  aMsg = ("SessionStore: " + aMsg).replace(/\S{80}/g, "$&\n");
  Cc["@mozilla.org/consoleservice;1"].getService(Ci.nsIConsoleService)
                                     .logStringMessage(aMsg);
}

/* :::::::: The Service ::::::::::::::: */

function SessionStoreService() {
}

SessionStoreService.prototype = {

/* ........ nsISessionStore API .............. */

  getBrowserState: function sss_getBrowserState(aBrowser) {
    dump("nsSessionStore::getBrowserState\n")
    return this._toJSONString(this._getWindowState(aBrowser));
  },

  setBrowserState: function sss_setBrowserState(aBrowser, aState) {
    dump("nsSessionStore::setBrowserState\n")
    this.restoreWindow(aBrowser, "(" + aState + ")");
  },

/* ........ Saving Functionality .............. */

  /**
   * Store all session data for a window
   * @param aSHistory
   *        nsISHistory reference
   */
  _saveWindowHistory: function sss_saveWindowHistory(aSHistory) {
    var entries = [];
    dump("nsSessionStore._saveWindowHistory " + aSHistory.count);
    for (var i = 0; i < aSHistory.count; i++) {
      entries.push(this._serializeHistoryEntry(aSHistory.getEntryAtIndex(i, false)));
    }

    return entries;
  },

  /**
   * Get an object that is a serialized representation of a History entry
   * Used for data storage
   * @param aEntry
   *        nsISHEntry instance
   * @returns object
   */
  _serializeHistoryEntry: function sss_serializeHistoryEntry(aEntry) {
    var entry = { url: aEntry.URI.spec, children: [] };
    
    if (aEntry.title && aEntry.title != entry.url) {
      entry.title = aEntry.title;
    }
    if (aEntry.isSubFrame) {
      entry.subframe = true;
    }
    if (!(aEntry instanceof Ci.nsISHEntry)) {
      return entry;
    }
    
    var cacheKey = aEntry.cacheKey;
    if (cacheKey && cacheKey instanceof Ci.nsISupportsPRUint32) {
      entry.cacheKey = cacheKey.data;
    }
    entry.ID = aEntry.ID;
    
    var x = {}, y = {};
    aEntry.getScrollPosition(x, y);
    entry.scroll = x.value + "," + y.value;
    
    try {
      var prefPostdata = this._prefBranch.getIntPref("sessionstore.postdata");
      if (prefPostdata && aEntry.postData && this._checkPrivacyLevel(aEntry.URI.schemeIs("https"))) {
        aEntry.postData.QueryInterface(Ci.nsISeekableStream).
                        seek(Ci.nsISeekableStream.NS_SEEK_SET, 0);
        var stream = Cc["@mozilla.org/scriptableinputstream;1"].
                     createInstance(Ci.nsIScriptableInputStream);
        stream.init(aEntry.postData);
        var postdata = stream.read(stream.available());
        if (prefPostdata == -1 || postdata.replace(/^(Content-.*\r\n)+(\r\n)*/, "").length <= prefPostdata) {
          entry.postdata = postdata;
        }
      }
    }
    catch (ex) { debug(ex); } // POSTDATA is tricky - especially since some extensions don't get it right
    
    if (!(aEntry instanceof Ci.nsISHContainer)) {
      return entry;
    }
    
    for (var i = 0; i < aEntry.childCount; i++) {
      var child = aEntry.GetChildAt(i);
      if (child) {
        entry.children.push(this._serializeHistoryEntry(child));
      }
      else { // to maintain the correct frame order, insert a dummy entry 
        entry.children.push({ url: "about:blank" });
      }
    }
    
    return entry;
  },

  /**
   * serialize session data for a window 
   * @param aBrowser
   *        Browser reference
   * @returns string
   */
  _getWindowState: function sss_getWindowState(aBrowser) {
    dump("nsSessionStore::_getWindowState: " + aBrowser + "\n")
    windowState = this._collectWindowData(aBrowser);

    /*    
    this._updateCookies(windowState);
    */

    return windowState;
  },

  _collectWindowData: function sss_collectWindowData(aBrowser) {
    dump("nsSessionStore::_collectWindowData\n")
    aBrowser.QueryInterface(Ci.nsIWebNavigation);
    historyState = this._saveWindowHistory(aBrowser.sessionHistory);
    /*
    this._updateTextAndScrollData(aWindow);
    this._updateCookieHosts(aWindow);
    this._updateWindowFeatures(aWindow);
    */
    
    return {history: historyState/*, textAndScroll: textAndScrollState*/};
  },

/* ........ Restoring Functionality .............. */

  /**
   * restore features to a single window
   * @param aBrowser
   *        Browser reference
   * @param aState
   *        JS object or its eval'able source
   */
  restoreWindow: function sss_restoreWindow(aBrowser, aState) {
    try {
      var winData = typeof aState == "string" ? this._safeEval(aState) : aState;
    }
    catch (ex) { // invalid state object - don't restore anything 
      debug(ex);
      dump(ex);
      return;
    }
    
    this.restoreHistoryPrecursor(aBrowser, winData.history);
  },

  /**
   * Manage history restoration for a window
   * @param aBrowser
   *        Browser reference
   * @param aHistoryData
   *        History data to be restored
   */
  restoreHistoryPrecursor: function sss_restoreHistoryPrecursor(aBrowser, aHistoryData) {
    /*
    // make sure that all browsers and their histories are available
    // - if one's not, resume this check in 100ms (repeat at most 10 times)
    for (var t = aIx; t < aTabs.length; t++) {
      try {
        if (!tabbrowser.getBrowserForTab(aTabs[t]._tab).webNavigation.sessionHistory) {
          throw new Error();
        }
      }
      catch (ex) { // in case browser or history aren't ready yet 
        if (aCount < 10) {
          var restoreHistoryFunc = function(self) {
            self.restoreHistoryPrecursor(aWindow, aTabs, aSelectTab, aIx, aCount + 1);
          }
          aWindow.setTimeout(restoreHistoryFunc, 100, this);
          return;
        }
      }
    }
    */

    // helper hash for ensuring unique frame IDs
    var aIdMap = { used: {} };
    this.restoreHistory(aBrowser, aHistoryData, aIdMap);
  },

  /**
   * Restory history for a window
   * @param aBrowser
   *        Browser reference
   * @param aHistoryData
   *        History data to be restored
   * @param aIdMap
   *        Hash for ensuring unique frame IDs
   */
  restoreHistory: function sss_restoreHistory(aBrowser, aHistoryData, aIdMap) {
    dump("nsSessionStore::restoreHistory\n")

    aBrowser.QueryInterface(Ci.nsIWebNavigation);
    aSHistory = aBrowser.sessionHistory;
    aSHistory.QueryInterface(Ci.nsISHistoryInternal);
    
    if (aSHistory.count > 0) {
      aSHistory.PurgeHistory(aSHistory.count);
    }
    
    if (!aHistoryData) {
      aHistoryData = [];
    }
    
    for (var i = 0; i < aHistoryData.length; i++) {
      aSHistory.addEntry(this._deserializeHistoryEntry(aHistoryData[i], aIdMap), true);
    }
    
    /*
    // make sure to reset the capabilities and attributes, in case this tab gets reused
    var disallow = (aHistoryData.disallow)?aHistoryData.disallow.split(","):[];
    CAPABILITIES.forEach(function(aCapability) {
      browser.docShell["allow" + aCapability] = disallow.indexOf(aCapability) == -1;
    });
    Array.filter(tab.attributes, function(aAttr) {
      return (_this.xulAttributes.indexOf(aAttr.name) > -1);
    }).forEach(tab.removeAttribute, tab);
    if (aHistoryData.xultab) {
      aHistoryData.xultab.split(" ").forEach(function(aAttr) {
        if (/^([^\s=]+)=(.*)/.test(aAttr)) {
          tab.setAttribute(RegExp.$1, decodeURI(RegExp.$2));
        }
      });
    }
    */
    try {
      aBrowser.gotoIndex(aHistoryData.length - 1);
    }
    catch (ex) { dump(ex + "\n"); } // ignore an invalid aHistoryData.index
  },

  /**
   * expands serialized history data into a session-history-entry instance
   * @param aEntry
   *        Object containing serialized history data for a URL
   * @param aIdMap
   *        Hash for ensuring unique frame IDs
   * @returns nsISHEntry
   */
  _deserializeHistoryEntry: function sss_deserializeHistoryEntry(aEntry, aIdMap) {
    var shEntry = Cc["@mozilla.org/browser/session-history-entry;1"].
                  createInstance(Ci.nsISHEntry);
    
    var ioService = Cc["@mozilla.org/network/io-service;1"].
                    getService(Ci.nsIIOService);
    shEntry.setURI(ioService.newURI(aEntry.url, null, null));
    shEntry.setTitle(aEntry.title || aEntry.url);
    shEntry.setIsSubFrame(aEntry.subframe || false);
    shEntry.loadType = Ci.nsIDocShellLoadInfo.loadHistory;
    
    if (aEntry.cacheKey) {
      var cacheKey = Cc["@mozilla.org/supports-PRUint32;1"].
                     createInstance(Ci.nsISupportsPRUint32);
      cacheKey.data = aEntry.cacheKey;
      shEntry.cacheKey = cacheKey;
    }
    if (aEntry.ID) {
      // get a new unique ID for this frame (since the one from the last
      // start might already be in use)
      var id = aIdMap[aEntry.ID] || 0;
      if (!id) {
        for (id = Date.now(); aIdMap.used[id]; id++);
        aIdMap[aEntry.ID] = id;
        aIdMap.used[id] = true;
      }
      shEntry.ID = id;
    }
    
    var scrollPos = (aEntry.scroll || "0,0").split(",");
    scrollPos = [parseInt(scrollPos[0]) || 0, parseInt(scrollPos[1]) || 0];
    shEntry.setScrollPosition(scrollPos[0], scrollPos[1]);
    
    if (aEntry.postdata) {
      var stream = Cc["@mozilla.org/io/string-input-stream;1"].
                   createInstance(Ci.nsIStringInputStream);
      stream.setData(aEntry.postdata, -1);
      shEntry.postData = stream;
    }
    
    if (aEntry.children && shEntry instanceof Ci.nsISHContainer) {
      for (var i = 0; i < aEntry.children.length; i++) {
        shEntry.AddChild(this._deserializeHistoryEntry(aEntry.children[i], aIdMap), i);
      }
    }
    
    return shEntry;
  },

/* ........ Auxiliary Functions .............. */

  /**
   * don't save sensitive data if the user doesn't want to
   * (distinguishes between encrypted and non-encrypted sites)
   * @param aIsHTTPS
   *        Bool is encrypted
   * @returns bool
   */
  _checkPrivacyLevel: function sss_checkPrivacyLevel(aIsHTTPS) {
    return this._prefBranch.getIntPref("sessionstore.privacy_level") < (aIsHTTPS ? PRIVACY_ENCRYPTED : PRIVACY_FULL);
  },

  /**
   * safe eval'ing
   */
  _safeEval: function sss_safeEval(aStr) {
    return Components.utils.evalInSandbox(aStr, EVAL_SANDBOX);
  },

  /**
   * Converts a JavaScript object into a JSON string
   * (see http://www.json.org/ for the full grammar).
   *
   * The inverse operation consists of eval("(" + JSON_string + ")");
   * and should be provably safe.
   *
   * @param aJSObject is the object to be converted
   * @return the object's JSON representation
   */
  _toJSONString: function sss_toJSONString(aJSObject) {
    // these characters have a special escape notation
    const charMap = { "\b": "\\b", "\t": "\\t", "\n": "\\n", "\f": "\\f",
                      "\r": "\\r", '"': '\\"', "\\": "\\\\" };
    // we use a single string builder for efficiency reasons
    var parts = [];
    
    // this recursive function walks through all objects and appends their
    // JSON representation to the string builder
    function jsonIfy(aObj) {
      if (typeof aObj == "boolean") {
        parts.push(aObj ? "true" : "false");
      }
      else if (typeof aObj == "number" && isFinite(aObj)) {
        // there is no representation for infinite numbers or for NaN!
        parts.push(aObj.toString());
      }
      else if (typeof aObj == "string") {
        aObj = aObj.replace(/[\\"\x00-\x1F\u0080-\uFFFF]/g, function($0) {
          // use the special escape notation if one exists, otherwise
          // produce a general unicode escape sequence
          return charMap[$0] ||
            "\\u" + ("0000" + $0.charCodeAt(0).toString(16)).slice(-4);
        });
        parts.push('"' + aObj + '"')
      }
      else if (aObj == null) {
        parts.push("null");
      }
      else if (aObj instanceof Array || aObj instanceof EVAL_SANDBOX.Array) {
        parts.push("[");
        for (var i = 0; i < aObj.length; i++) {
          jsonIfy(aObj[i]);
          parts.push(",");
        }
        if (parts[parts.length - 1] == ",")
          parts.pop(); // drop the trailing colon
        parts.push("]");
      }
      else if (typeof aObj == "object") {
        parts.push("{");
        for (var key in aObj) {
          jsonIfy(key.toString());
          parts.push(":");
          jsonIfy(aObj[key]);
          parts.push(",");
        }
        if (parts[parts.length - 1] == ",")
          parts.pop(); // drop the trailing colon
        parts.push("}");
      }
      else {
        throw new Error("No JSON representation for this object!");
      }
    }
    jsonIfy(aJSObject);
    
    var newJSONString = parts.join(" ");
    // sanity check - so that API consumers can just eval this string
    if (/[^,:{}\[\]0-9.\-+Eaeflnr-u \n\r\t]/.test(
      newJSONString.replace(/"(\\.|[^"\\])*"/g, "")
    ))
      throw new Error("JSON conversion failed unexpectedly!");
    
    return newJSONString;
  },

/* ........ QueryInterface .............. */

  QueryInterface: function(aIID) {
    if (!aIID.equals(Ci.nsISupports) && 
      !aIID.equals(Ci.nsIObserver) && 
      !aIID.equals(Ci.nsISupportsWeakReference) && 
      !aIID.equals(Ci.nsIDOMEventListener) &&
      !aIID.equals(Ci.nsISessionStore)) {
      Components.returnCode = Cr.NS_ERROR_NO_INTERFACE;
      return null;
    }
    
    return this;
  }
};

/* :::::::: Service Registration & Initialization ::::::::::::::: */

/* ........ nsIModule .............. */

const SessionStoreModule = {

  getClassObject: function(aCompMgr, aCID, aIID) {
    if (aCID.equals(CID)) {
      return SessionStoreFactory;
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

const SessionStoreFactory = {

  createInstance: function(aOuter, aIID) {
    if (aOuter != null) {
      Components.returnCode = Cr.NS_ERROR_NO_AGGREGATION;
      return null;
    }
    
    return (new SessionStoreService()).QueryInterface(aIID);
  },

  lockFactory: function(aLock) { },

  QueryInterface: function(aIID) {
    if (!aIID.equals(Ci.nsISupports) && !aIID.equals(Ci.nsIModule) &&
        !aIID.equals(Ci.nsIFactory) && !aIID.equals(Ci.nsISessionStore)) {
      Components.returnCode = Cr.NS_ERROR_NO_INTERFACE;
      return null;
    }
    
    return this;
  }
};

function NSGetModule(aComMgr, aFileSpec) {
  dump("nsSessionStore: NSGetModule\n")
  return SessionStoreModule;
}
