/*
 * Copyright (C) 2006, Red Hat, Inc.
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library; if not, write to the
 * Free Software Foundation, Inc., 59 Temple Place - Suite 330,
 * Boston, MA 02111-1307, USA.
 */

#include <config.h>

#include "sugar-browser.h"
#include "sugar-marshal.h"
#include "GeckoContentHandler.h"
#include "GeckoDownload.h"
#include "GeckoDragDropHooks.h"
#include "GeckoDocumentObject.h"
#include "GeckoBrowserPersist.h"

#include <gdk/gdkx.h>
#include <gtkmozembed_internal.h>
#include <nsCOMPtr.h>
#include <nsIPrefService.h>
#include <nsServiceManagerUtils.h>
#include <nsStringAPI.h>
#include <nsILocalFile.h>
#include <nsIWebBrowser.h>
#include <nsIWebBrowserFocus.h>
#include <nsIWebBrowserPersist.h>
#include <nsIDOMWindow.h>
#include <nsIDOMWindowUtils.h>
#include <nsIDOMDocument.h>
#include <nsIDOMMouseEvent.h>
#include <nsIGenericFactory.h>
#include <nsIHelperAppLauncherDialog.h>
#include <nsIComponentRegistrar.h>
#include <nsIDOMNode.h>
#include <nsIDOMEventTarget.h>
#include <nsIDOMHTMLImageElement.h>
#include <nsIIOService.h>
#include <nsComponentManagerUtils.h>
#include <imgICache.h>
#include <nsIProperties.h>
#include <nsIWebNavigation.h>
#include <nsISupportsPrimitives.h>
#include <nsIInterfaceRequestorUtils.h>
#include <nsIMIMEHeaderParam.h>
#include <nsISHistory.h>
#include <nsIHistoryEntry.h>
#include <nsISHEntry.h>
#include <nsIInputStream.h>
#include <nsICommandManager.h>
#include <nsIClipboardDragDropHooks.h>

enum {
	PROP_0,
	PROP_PROGRESS,
	PROP_TITLE,
	PROP_ADDRESS,
	PROP_CAN_GO_BACK,
	PROP_CAN_GO_FORWARD,
	PROP_LOADING,
    PROP_DOCUMENT_METADATA
};

enum {
    MOUSE_CLICK,
    N_SIGNALS
};

static guint signals[N_SIGNALS];

static GObjectClass *parent_class = NULL;

static const nsModuleComponentInfo sSugarComponents[] = {
	{
		"Gecko Content Handler",
		GECKOCONTENTHANDLER_CID,
		NS_IHELPERAPPLAUNCHERDLG_CONTRACTID,
		NULL
	},
	{
		"Gecko Download",
		GECKODOWNLOAD_CID,
		NS_TRANSFER_CONTRACTID,
		NULL
	}
};

int (*old_handler) (Display *, XErrorEvent *);

static int
error_handler (Display *d, XErrorEvent *e)
{
    gchar buf[64];
    gchar *msg;

    XGetErrorText(d, e->error_code, buf, 63);

    msg =
    g_strdup_printf("The program '%s' received an X Window System error.\n"
                    "This probably reflects a bug in the program.\n"
                    "The error was '%s'.\n"
                    "  (Details: serial %ld error_code %d request_code %d minor_code %d)\n",
                    g_get_prgname (),
                    buf,
                    e->serial, 
                    e->error_code, 
                    e->request_code,
                    e->minor_code);

    g_warning ("%s", msg);

    return 0;
    /*return (*old_handler)(d, e);*/
}

static void
setup_plugin_path ()
{
    const char *user_path;
    char *new_path;

    user_path = g_getenv ("MOZ_PLUGIN_PATH");
    new_path = g_strconcat (user_path ? user_path : "",
                            user_path ? ":" : "",
                            PLUGIN_DIR,
                            (char *) NULL);
    g_setenv ("MOZ_PLUGIN_PATH", new_path, TRUE);
    g_free (new_path);
}

gboolean
sugar_browser_startup(const char *profile_path, const char *profile_name)
{
	nsresult rv;

    setup_plugin_path();

	gtk_moz_embed_set_profile_path(profile_path, profile_name);

    old_handler = XSetErrorHandler(error_handler);

    gtk_moz_embed_push_startup();

	nsCOMPtr<nsIPrefService> prefService;
	prefService = do_GetService(NS_PREFSERVICE_CONTRACTID);
	NS_ENSURE_TRUE(prefService, FALSE);

	/* Read our predefined default prefs */
	nsCOMPtr<nsILocalFile> file;
	NS_NewNativeLocalFile(nsCString(SHARE_DIR"/gecko-prefs.js"),
						  PR_TRUE, getter_AddRefs(file));
	NS_ENSURE_TRUE(file, FALSE);

	rv = prefService->ReadUserPrefs (file);
	if (NS_FAILED(rv)) {
		g_warning ("failed to read default preferences, error: %x", rv);
		return FALSE;
	}

	nsCOMPtr<nsIPrefBranch> pref;
	prefService->GetBranch ("", getter_AddRefs(pref));
	NS_ENSURE_TRUE(pref, FALSE);

    pref->SetCharPref ("helpers.private_mime_types_file", SHARE_DIR"/mime.types");

	rv = prefService->ReadUserPrefs (nsnull);
	if (NS_FAILED(rv)) {
		g_warning ("failed to read user preferences, error: %x", rv);
	}

	nsCOMPtr<nsIComponentRegistrar> componentRegistrar;
	NS_GetComponentRegistrar(getter_AddRefs(componentRegistrar));
	NS_ENSURE_TRUE (componentRegistrar, FALSE);

    nsCOMPtr<nsIFactory> contentHandlerFactory;
    rv = NS_NewGeckoContentHandlerFactory(getter_AddRefs(contentHandlerFactory));
    rv = componentRegistrar->RegisterFactory(sSugarComponents[0].mCID,
                                             sSugarComponents[0].mDescription,
                                             sSugarComponents[0].mContractID,
                                             contentHandlerFactory);
	if (NS_FAILED(rv)) {
		g_warning ("Failed to register factory for %s\n", sSugarComponents[0].mDescription);
		return FALSE;
	}

    nsCOMPtr<nsIFactory> downloadFactory;
    rv = NS_NewGeckoDownloadFactory(getter_AddRefs(downloadFactory));
    rv = componentRegistrar->RegisterFactory(sSugarComponents[1].mCID,
                                             sSugarComponents[1].mDescription,
                                             sSugarComponents[1].mContractID,
                                             downloadFactory);
	if (NS_FAILED(rv)) {
		g_warning ("Failed to register factory for %s\n", sSugarComponents[1].mDescription);
		return FALSE;
	}

	return TRUE;
}

void
sugar_browser_shutdown(void)
{
    gtk_moz_embed_pop_startup();
}

G_DEFINE_TYPE(SugarBrowser, sugar_browser, GTK_TYPE_MOZ_EMBED)

static nsresult
FilenameFromContentDisposition(nsCString contentDisposition, nsCString &fileName)
{
    nsresult rv;

    nsCString fallbackCharset;

    nsCOMPtr<nsIMIMEHeaderParam> mimehdrpar =
        do_GetService("@mozilla.org/network/mime-hdrparam;1");
    NS_ENSURE_TRUE(mimehdrpar, NS_ERROR_FAILURE);

    nsString aFileName;
    rv = mimehdrpar->GetParameter (contentDisposition, "filename",
                                   fallbackCharset, PR_TRUE, nsnull,
                                   aFileName);

    if (NS_FAILED(rv) || !fileName.Length()) {
        rv = mimehdrpar->GetParameter (contentDisposition, "name",
                                       fallbackCharset, PR_TRUE, nsnull,
                                       aFileName);
    }

    if (NS_SUCCEEDED(rv) && fileName.Length()) {
        NS_UTF16ToCString (aFileName, NS_CSTRING_ENCODING_UTF8, fileName);
    }

    return NS_OK;
}

static SugarBrowserMetadata *
sugar_browser_get_document_metadata(SugarBrowser *browser)
{
    SugarBrowserMetadata *metadata = sugar_browser_metadata_new();

#ifdef HAVE_NS_WEB_BROWSER
	nsCOMPtr<nsIWebBrowser> webBrowser;
	gtk_moz_embed_get_nsIWebBrowser(GTK_MOZ_EMBED(browser),
									getter_AddRefs(webBrowser));
	NS_ENSURE_TRUE(webBrowser, metadata);

    nsCOMPtr<nsIDOMWindow> DOMWindow;
    webBrowser->GetContentDOMWindow(getter_AddRefs(DOMWindow));
	NS_ENSURE_TRUE(DOMWindow, metadata);

    nsCOMPtr<nsIDOMWindowUtils> DOMWindowUtils(do_GetInterface(DOMWindow));
	NS_ENSURE_TRUE(DOMWindowUtils, metadata);

    const PRUnichar contentDispositionLiteral[] =
        {'c', 'o', 'n', 't', 'e', 'n', 't', '-', 'd', 'i', 's', 'p',
         'o', 's', 'i', 't', 'i', 'o', 'n', '\0'};

    nsString contentDisposition;
    DOMWindowUtils->GetDocumentMetadata(nsString(contentDispositionLiteral),
                                        contentDisposition);

    nsCString cContentDisposition;
    NS_UTF16ToCString (contentDisposition, NS_CSTRING_ENCODING_UTF8,
                       cContentDisposition);

    nsCString fileName;
    FilenameFromContentDisposition(cContentDisposition, fileName);

    if (!fileName.Length()) {
        nsCOMPtr<nsIWebNavigation> webNav(do_QueryInterface(webBrowser));
        if (webNav) {
            nsCOMPtr<nsIURI> docURI;
            webNav->GetCurrentURI (getter_AddRefs(docURI));

            nsCOMPtr<nsIURL> url(do_QueryInterface(docURI));
            if (url) {
                url->GetFileName(fileName);
            }
        }
    }

    if (fileName.Length()) {
        metadata->filename = g_strdup(fileName.get());
    }
#endif

    return metadata;
}

static void
sugar_browser_get_property(GObject         *object,
						   guint            prop_id,
						   GValue          *value,
						   GParamSpec      *pspec)
{
	SugarBrowser *browser = SUGAR_BROWSER(object);

	switch (prop_id) {
	    case PROP_PROGRESS:
			g_value_set_double(value, browser->progress);
		break;
	    case PROP_ADDRESS:
			g_value_set_string(value, browser->address);
		break;
	    case PROP_TITLE:
			g_value_set_string(value, browser->title);
		break;
	    case PROP_CAN_GO_BACK:
			g_value_set_boolean(value, browser->can_go_back);
		break;
	    case PROP_CAN_GO_FORWARD:
			g_value_set_boolean(value, browser->can_go_forward);
		break;
	    case PROP_LOADING:
			g_value_set_boolean(value, browser->loading);
		break;
	    case PROP_DOCUMENT_METADATA:
            SugarBrowserMetadata *metadata;
            metadata = sugar_browser_get_document_metadata(browser);
			g_value_set_boxed(value, metadata);
		break;
		default:
			G_OBJECT_WARN_INVALID_PROPERTY_ID (object, prop_id, pspec);
		break;
	}
}

static void
sugar_browser_realize(GtkWidget *widget)
{
    GTK_WIDGET_CLASS(parent_class)->realize(widget);

#ifdef HAVE_NS_WEB_BROWSER
       GtkMozEmbed *embed = GTK_MOZ_EMBED(widget);
       nsCOMPtr<nsIWebBrowser> webBrowser;
       gtk_moz_embed_get_nsIWebBrowser(embed, getter_AddRefs(webBrowser));
       NS_ENSURE_TRUE(webBrowser, );

    nsCOMPtr<nsICommandManager> commandManager = do_GetInterface(webBrowser);
    if (commandManager) {
        nsresult rv;
        nsIClipboardDragDropHooks *rawPtr = new GeckoDragDropHooks(
            SUGAR_BROWSER(widget));
        nsCOMPtr<nsIClipboardDragDropHooks> geckoDragDropHooks(
            do_QueryInterface(rawPtr, &rv));
        NS_ENSURE_SUCCESS(rv, );

        nsCOMPtr<nsIDOMWindow> DOMWindow = do_GetInterface(webBrowser); 
        nsCOMPtr<nsICommandParams> cmdParamsObj = do_CreateInstance(
            NS_COMMAND_PARAMS_CONTRACTID, &rv);
        NS_ENSURE_SUCCESS(rv, );
        cmdParamsObj->SetISupportsValue("addhook", geckoDragDropHooks);
        commandManager->DoCommand("cmd_clipboardDragDropHook", cmdParamsObj,
                                  DOMWindow);
    }
#endif
}

static void
sugar_browser_class_init(SugarBrowserClass *browser_class)
{
    GObjectClass    *gobject_class = G_OBJECT_CLASS(browser_class);
    GtkWidgetClass  *widget_class = GTK_WIDGET_CLASS(browser_class);

    parent_class = (GObjectClass *) g_type_class_peek_parent(browser_class);

    gobject_class->get_property = sugar_browser_get_property;
    widget_class->realize = sugar_browser_realize;

    signals[MOUSE_CLICK] = g_signal_new ("mouse_click",
                                SUGAR_TYPE_BROWSER,
                                G_SIGNAL_RUN_LAST,
                                G_STRUCT_OFFSET(SugarBrowser, mouse_click),
                                g_signal_accumulator_true_handled, NULL,
                                sugar_marshal_BOOLEAN__BOXED,
                                G_TYPE_BOOLEAN,
                                1,
                                SUGAR_TYPE_BROWSER_EVENT);

	g_object_class_install_property(gobject_class, PROP_PROGRESS,
                                    g_param_spec_double ("progress",
                                                         "Progress",
                                                         "Progress",
                                                         0.0, 1.0, 0.0,
                                                         G_PARAM_READABLE));

	g_object_class_install_property (gobject_class, PROP_ADDRESS,
									 g_param_spec_string ("address",
														  "Address",
														  "Address",
                                                          "",
														  G_PARAM_READABLE));

	g_object_class_install_property (gobject_class, PROP_TITLE,
									 g_param_spec_string ("title",
														  "Title",
														  "Title",
                                                          "",
														  G_PARAM_READABLE));

	g_object_class_install_property (gobject_class, PROP_CAN_GO_BACK,
									 g_param_spec_boolean ("can-go-back",
														   "Can go back",
														   "Can go back",
														   FALSE,
														   G_PARAM_READABLE));

	g_object_class_install_property (gobject_class, PROP_CAN_GO_FORWARD,
									 g_param_spec_boolean ("can-go-forward",
														   "Can go forward",
														   "Can go forward",
														   FALSE,
														   G_PARAM_READABLE));

	g_object_class_install_property (gobject_class, PROP_LOADING,
									 g_param_spec_boolean ("loading",
														   "Loading",
														   "Loading",
														   FALSE,
														   G_PARAM_READABLE));

    g_object_class_install_property(gobject_class, PROP_DOCUMENT_METADATA,
                                    g_param_spec_boxed("document-metadata",
                                                       "Document Metadata",
                                                       "Document metadata",
                                                       SUGAR_TYPE_BROWSER_METADATA,
                                                       G_PARAM_READABLE));

}

SugarBrowser *
sugar_browser_create_window(SugarBrowser *browser)
{
	return SUGAR_BROWSER_GET_CLASS(browser)->create_window(browser);
}

static void
update_navigation_properties(SugarBrowser *browser)
{
	GtkMozEmbed *embed = GTK_MOZ_EMBED(browser);
	gboolean can_go_back;
	gboolean can_go_forward;

	can_go_back = gtk_moz_embed_can_go_back(embed);
	if (can_go_back != browser->can_go_back) {
		browser->can_go_back = can_go_back;
		g_object_notify (G_OBJECT(browser), "can-go-back");
	}

	can_go_forward = gtk_moz_embed_can_go_forward(embed);
	if (can_go_forward != browser->can_go_forward) {
		browser->can_go_forward = can_go_forward;
		g_object_notify (G_OBJECT(browser), "can-go-forward");
	}
}

static void
new_window_cb(GtkMozEmbed  *embed,
			  GtkMozEmbed **newEmbed,
              guint         chromemask)
{
	SugarBrowser *browser;

	browser = sugar_browser_create_window(SUGAR_BROWSER(embed));

	*newEmbed = GTK_MOZ_EMBED(browser);
}

static void
sugar_browser_set_progress(SugarBrowser *browser, float progress)
{
	g_return_if_fail(SUGAR_IS_BROWSER(browser));

	browser->progress = progress;
	g_object_notify (G_OBJECT(browser), "progress");
}

static void
sugar_browser_set_loading(SugarBrowser *browser, gboolean loading)
{
	g_return_if_fail(SUGAR_IS_BROWSER(browser));

	browser->loading = loading;
	g_object_notify (G_OBJECT(browser), "loading");
}

static void
net_state_cb(GtkMozEmbed *embed, const char *aURI, gint state, guint status)
{
	SugarBrowser *browser = SUGAR_BROWSER(embed);

	if (state & GTK_MOZ_EMBED_FLAG_IS_NETWORK) {
		if (state & GTK_MOZ_EMBED_FLAG_START) {
			browser->total_requests = 0;
			browser->current_requests = 0;

			sugar_browser_set_progress(browser, 0.03);
			sugar_browser_set_loading(browser, TRUE);
            update_navigation_properties(browser);
		} else if (state & GTK_MOZ_EMBED_FLAG_STOP) {
			sugar_browser_set_progress(browser, 1.0);
			sugar_browser_set_loading(browser, FALSE);
            update_navigation_properties(browser);
		}
	}

	if (state & GTK_MOZ_EMBED_FLAG_IS_REQUEST) {
		float progress;

		if (state & GTK_MOZ_EMBED_FLAG_START) {
			browser->total_requests++;
		}
		else if (state & GTK_MOZ_EMBED_FLAG_STOP)
		{
			browser->current_requests++;
		}

		progress = float(browser->current_requests) /
				   float(browser->total_requests);
		if (progress > browser->progress) {
			sugar_browser_set_progress(browser, progress);
		}
	}
}

static void
title_cb(GtkMozEmbed *embed)
{
	SugarBrowser *browser = SUGAR_BROWSER(embed);

	g_free(browser->title);
	browser->title = gtk_moz_embed_get_title(embed);

	g_object_notify (G_OBJECT(browser), "title");
}

static void
location_cb(GtkMozEmbed *embed)
{
	SugarBrowser *browser = SUGAR_BROWSER(embed);

	g_free(browser->address);
	browser->address = gtk_moz_embed_get_location(embed);

	g_object_notify (G_OBJECT(browser), "address");

	update_navigation_properties(browser);
}

static gboolean
dom_mouse_click_cb(GtkMozEmbed *embed, nsIDOMMouseEvent *mouseEvent)
{
	SugarBrowser *browser = SUGAR_BROWSER(embed);
    SugarBrowserEvent *event;
    gint return_value = FALSE;

    nsCOMPtr<nsIDOMEventTarget> eventTarget;
    mouseEvent->GetTarget(getter_AddRefs(eventTarget));
    NS_ENSURE_TRUE(mouseEvent, FALSE);

    nsCOMPtr<nsIDOMNode> targetNode;
    targetNode = do_QueryInterface(eventTarget);
    NS_ENSURE_TRUE(targetNode, FALSE);

    event = sugar_browser_event_new();

    GeckoDocumentObject documentObject(browser, targetNode);
    if(documentObject.IsImage()) {
        event->image_uri = documentObject.GetImageURI();
        event->image_name = documentObject.GetImageName();
    }

    PRUint16 btn = 0;
    mouseEvent->GetButton (&btn);
    event->button = btn + 1;

    g_signal_emit(browser, signals[MOUSE_CLICK], 0, event, &return_value);

    sugar_browser_event_free(event);

    return return_value;
}

static void
sugar_browser_init(SugarBrowser *browser)
{
	browser->title = NULL;
	browser->address = NULL;
	browser->progress = 0.0;

	g_signal_connect(G_OBJECT(browser), "new-window",
					 G_CALLBACK(new_window_cb), NULL);
	g_signal_connect(G_OBJECT(browser), "net-state-all",
					 G_CALLBACK(net_state_cb), NULL);
	g_signal_connect(G_OBJECT(browser), "title",
					 G_CALLBACK(title_cb), NULL);
	g_signal_connect(G_OBJECT(browser), "location",
					 G_CALLBACK(location_cb), NULL);
	g_signal_connect(G_OBJECT(browser), "dom-mouse-click",
					 G_CALLBACK(dom_mouse_click_cb), NULL);
}

void
sugar_browser_scroll_pixels(SugarBrowser *browser,
                            int           dx,
                            int           dy)
{
#ifndef HAVE_GECKO_1_9
	nsCOMPtr<nsIWebBrowser> webBrowser;
	gtk_moz_embed_get_nsIWebBrowser (GTK_MOZ_EMBED(browser),
									 getter_AddRefs(webBrowser));
	NS_ENSURE_TRUE (webBrowser, );

	nsCOMPtr<nsIWebBrowserFocus> webBrowserFocus;
	webBrowserFocus = do_QueryInterface (webBrowser);
	NS_ENSURE_TRUE (webBrowserFocus, );

	nsCOMPtr<nsIDOMWindow> DOMWindow;
	webBrowserFocus->GetFocusedWindow (getter_AddRefs(DOMWindow));
	if (!DOMWindow) {
		webBrowser->GetContentDOMWindow (getter_AddRefs(DOMWindow));
	}
	NS_ENSURE_TRUE (DOMWindow, );

	DOMWindow->ScrollBy (dx, dy);
#endif
}

void
sugar_browser_grab_focus(SugarBrowser *browser)
{
	GtkWidget *child;

	child = gtk_bin_get_child(GTK_BIN(browser));

	if (child != NULL) {
		gtk_widget_grab_focus (child);
	} else {
		g_warning ("Need to realize the embed before grabbing focus!\n");
	}
}

gboolean
sugar_browser_save_uri(SugarBrowser *browser,
                       const char   *uri,
                       const char   *filename)
{
    GeckoBrowserPersist browserPersist(browser);
    return browserPersist.SaveURI(uri, filename);
}

gboolean
sugar_browser_save_document(SugarBrowser *browser,
                            const char   *filename)
{
#ifdef HAVE_NS_WEB_BROWSER
    nsresult rv;

    nsCString cFile(filename);

    nsCOMPtr<nsILocalFile> destFile = do_CreateInstance("@mozilla.org/file/local;1");
    NS_ENSURE_TRUE(destFile, FALSE);

    destFile->InitWithNativePath(cFile);

    GString *path = g_string_new (filename);
    char *dot_pos = strchr (path->str, '.');
    if (dot_pos) {
        g_string_truncate (path, dot_pos - path->str);
    }
    g_string_append (path, " Files");

    nsCOMPtr<nsILocalFile> filesFolder;    
    filesFolder = do_CreateInstance ("@mozilla.org/file/local;1");
    filesFolder->InitWithNativePath (nsCString(path->str));

    g_string_free (path, TRUE);

	nsCOMPtr<nsIWebBrowser> webBrowser;
	gtk_moz_embed_get_nsIWebBrowser(GTK_MOZ_EMBED(browser),
									getter_AddRefs(webBrowser));
	NS_ENSURE_TRUE(webBrowser, FALSE);

    nsCOMPtr<nsIDOMWindow> DOMWindow;
    webBrowser->GetContentDOMWindow(getter_AddRefs(DOMWindow));
	NS_ENSURE_TRUE(DOMWindow, FALSE);

    nsCOMPtr<nsIDOMDocument> DOMDocument;
    DOMWindow->GetDocument (getter_AddRefs(DOMDocument));
	NS_ENSURE_TRUE(DOMDocument, FALSE);

	nsCOMPtr<nsIWebBrowserPersist> webPersist = do_QueryInterface (webBrowser);
	NS_ENSURE_TRUE(webPersist, FALSE);

    rv = webPersist->SaveDocument(DOMDocument, destFile, filesFolder, nsnull, 0, 0);
    NS_ENSURE_SUCCESS(rv, FALSE);

    return TRUE;
#else
    return FALSE;
#endif
}

GType
sugar_browser_event_get_type(void)
{
    static GType type = 0;

    if (G_UNLIKELY(type == 0)) {
        type = g_boxed_type_register_static("SugarBrowserEvent",
                            (GBoxedCopyFunc)sugar_browser_event_copy,
                            (GBoxedFreeFunc)sugar_browser_event_free);
    }

    return type;
}

SugarBrowserEvent *
sugar_browser_event_new(void)
{
    SugarBrowserEvent *event;

    event = g_new0(SugarBrowserEvent, 1);

    return event;
}

SugarBrowserEvent *
sugar_browser_event_copy(SugarBrowserEvent *event)
{
    SugarBrowserEvent *copy;

    g_return_val_if_fail(event != NULL, NULL);

    copy = g_new0(SugarBrowserEvent, 1);
    copy->button = event->button;
    copy->image_uri = g_strdup(event->image_uri);
    copy->image_name = g_strdup(event->image_name);

    return copy;
}

void
sugar_browser_event_free(SugarBrowserEvent *event)
{
    g_return_if_fail(event != NULL);

    if (event->image_uri) {
        g_free(event->image_uri);
    }
    if (event->image_name) {
        g_free(event->image_name);
    }

    g_free(event);
}

GType
sugar_browser_metadata_get_type(void)
{
    static GType type = 0;

    if (G_UNLIKELY(type == 0)) {
        type = g_boxed_type_register_static("SugarBrowserMetadata",
                            (GBoxedCopyFunc)sugar_browser_metadata_copy,
                            (GBoxedFreeFunc)sugar_browser_metadata_free);
    }

    return type;
}

SugarBrowserMetadata *
sugar_browser_metadata_new(void)
{
    SugarBrowserMetadata *metadata;

    metadata = g_new0(SugarBrowserMetadata, 1);

    return metadata;
}

SugarBrowserMetadata *
sugar_browser_metadata_copy(SugarBrowserMetadata *metadata)
{
    SugarBrowserMetadata *copy;

    g_return_val_if_fail(metadata != NULL, NULL);

    copy = g_new0(SugarBrowserMetadata, 1);
    copy->filename = g_strdup(metadata->filename);

    return copy;
}

void
sugar_browser_metadata_free(SugarBrowserMetadata *metadata)
{
    g_return_if_fail(metadata != NULL);

    if (metadata->filename) {
        g_free(metadata->filename);
    }

    g_free(metadata);
}
