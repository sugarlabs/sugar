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

#include "sugar-browser.h"
#include "GeckoContentHandler.h"
#include "GeckoDownload.h"

#include <gtkmozembed_internal.h>
#include <nsCOMPtr.h>
#include <nsIPrefService.h>
#include <nsServiceManagerUtils.h>
#include <nsStringAPI.h>
#include <nsILocalFile.h>
#include <nsIWebBrowser.h>
#include <nsIWebBrowserFocus.h>
#include <nsIDOMWindow.h>
#include <nsIGenericFactory.h>
#include <nsIHelperAppLauncherDialog.h>
#include <nsIComponentRegistrar.h>
#include <nsIComponentManager.h>

NS_GENERIC_FACTORY_CONSTRUCTOR(GeckoContentHandler)
NS_GENERIC_FACTORY_CONSTRUCTOR(GeckoDownload)

enum {
	PROP_0,
	PROP_PROGRESS,
	PROP_TITLE,
	PROP_ADDRESS,
	PROP_CAN_GO_BACK,
	PROP_CAN_GO_FORWARD,
	PROP_LOADING
};

static const nsModuleComponentInfo sSugarComponents[] = {
	{
		"Gecko Content Handler",
		GECKOCONTENTHANDLER_CID,
		NS_IHELPERAPPLAUNCHERDLG_CONTRACTID,
		GeckoContentHandlerConstructor
	},
	{
		"Gecko Download",
		GECKODOWNLOAD_CID,
		NS_TRANSFER_CONTRACTID,
		GeckoDownloadConstructor
	}
};

gboolean
sugar_browser_startup(const char *profile_path, const char *profile_name)
{
	nsresult rv;

	gtk_moz_embed_set_profile_path(profile_path, profile_name);

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

	rv = prefService->ReadUserPrefs (nsnull);
	if (NS_FAILED(rv)) {
		g_warning ("failed to read user preferences, error: %x", rv);
	}

	/* Register our components */
	nsCOMPtr<nsIComponentRegistrar> componentRegistrar;
	NS_GetComponentRegistrar(getter_AddRefs(componentRegistrar));
	NS_ENSURE_TRUE (componentRegistrar, FALSE);

	nsCOMPtr<nsIComponentManager> componentManager;
	NS_GetComponentManager (getter_AddRefs (componentManager));
	NS_ENSURE_TRUE (componentManager, FALSE);
	
	for (guint i = 0; i < G_N_ELEMENTS(sSugarComponents); i++) {
	
		nsCOMPtr<nsIGenericFactory> componentFactory;
		rv = NS_NewGenericFactory(getter_AddRefs(componentFactory), 
								  &(sSugarComponents[i]));
		if (NS_FAILED(rv) || !componentFactory) {
			g_warning ("Failed to make a factory for %s\n", sSugarComponents[i].mDescription);
			return FALSE;
		}

		rv = componentRegistrar->RegisterFactory(sSugarComponents[i].mCID,
						 sSugarComponents[i].mDescription,
						 sSugarComponents[i].mContractID,
						 componentFactory);
		if (NS_FAILED(rv)) {
			g_warning ("Failed to register factory for %s\n", sSugarComponents[i].mDescription);
			return FALSE;
		}

		if (sSugarComponents[i].mRegisterSelfProc) {
			rv = sSugarComponents[i].mRegisterSelfProc(componentManager, nsnull, 
													   nsnull, nsnull, 
													   &sSugarComponents[i]);
			if (NS_FAILED(rv)) {
				g_warning ("Failed to register-self for %s\n", sSugarComponents[i].mDescription);
				return FALSE;
			}
		}
	}
	
	return TRUE;
}

void
sugar_browser_shutdown(void)
{
    gtk_moz_embed_pop_startup();
}

G_DEFINE_TYPE(SugarBrowser, sugar_browser, GTK_TYPE_MOZ_EMBED)

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
		default:
			G_OBJECT_WARN_INVALID_PROPERTY_ID (object, prop_id, pspec);
		break;
	}
}


static void
sugar_browser_class_init(SugarBrowserClass *browser_class)
{
	GObjectClass *gobject_class = G_OBJECT_CLASS(browser_class);

	gobject_class->get_property = sugar_browser_get_property;

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
		} else if (state & GTK_MOZ_EMBED_FLAG_STOP) {
			sugar_browser_set_progress(browser, 1.0);
			sugar_browser_set_loading(browser, FALSE);
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
}

void
sugar_browser_scroll_pixels(SugarBrowser *browser,
                            int           dx,
                            int           dy)
{
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
		webBrowser->GetContentDOMWindow (getter_AddRefs (DOMWindow));
	}
	NS_ENSURE_TRUE (DOMWindow, );

	DOMWindow->ScrollBy (dx, dy);
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
