/* 
 * Copyright (C) 2006 Red Hat, Inc
 *
 * Sugar is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * Sugar is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.
 */

#include "gecko-browser.h"

#include <nsCOMPtr.h>
#include <nsIPrefService.h>
#include <nsServiceManagerUtils.h>

enum {
	PROP_0,
	PROP_PROGRESS
};

void
gecko_browser_startup(void)
{
	nsCOMPtr<nsIPrefService> prefService;

	prefService = do_GetService(NS_PREFSERVICE_CONTRACTID);
	NS_ENSURE_TRUE(prefService, );

	nsCOMPtr<nsIPrefBranch> pref;
	prefService->GetBranch("", getter_AddRefs(pref));
	NS_ENSURE_TRUE(pref, );

	pref->SetBoolPref ("dom.disable_open_during_load", TRUE);
} 

G_DEFINE_TYPE(GeckoBrowser, gecko_browser, GTK_TYPE_MOZ_EMBED)

//static guint signals[N_SIGNALS];

GeckoBrowser *
gecko_browser_new(void)
{
	return GECKO_BROWSER(g_object_new(GECKO_TYPE_BROWSER, NULL));
}

static void
gecko_browser_get_property(GObject         *object,
						   guint            prop_id,
						   GValue          *value,
						   GParamSpec      *pspec)
{
	GeckoBrowser *browser = GECKO_BROWSER(object);

	switch (prop_id) {
	    case PROP_PROGRESS:
			g_value_set_double(value, browser->progress);
		break;

		default:
			G_OBJECT_WARN_INVALID_PROPERTY_ID (object, prop_id, pspec);
		break;
	}
}


static void
gecko_browser_class_init(GeckoBrowserClass *browser_class)
{
	GObjectClass *gobject_class = G_OBJECT_CLASS(browser_class);

	gobject_class->get_property = gecko_browser_get_property;

	g_object_class_install_property (gobject_class, PROP_PROGRESS,
                                     g_param_spec_double ("progress",
                                                          "Progress",
                                                          "Progress",
                                                          0.0, 1.0, 0.0,
                                                          G_PARAM_READABLE));
}

GeckoBrowser *
gecko_browser_create_window(GeckoBrowser *browser)
{
	return GECKO_BROWSER_GET_CLASS(browser)->create_window(browser);
}

static void
new_window_cb(GtkMozEmbed  *embed,
			  GtkMozEmbed **newEmbed,
              guint         chromemask)
{
	GeckoBrowser *browser;

	browser = gecko_browser_create_window(GECKO_BROWSER(embed));

	*newEmbed = GTK_MOZ_EMBED(browser);
}

static void
gecko_browser_set_progress(GeckoBrowser *browser, float progress)
{
	g_return_if_fail(GECKO_IS_BROWSER(browser));

	browser->progress = progress;
	g_object_notify (G_OBJECT(browser), "progress");
}

static void
net_state_cb(GtkMozEmbed *embed, const char *aURI, gint state, guint status)
{
	GeckoBrowser *browser = GECKO_BROWSER(embed);

	if (state & GTK_MOZ_EMBED_FLAG_IS_NETWORK) {
		if (state & GTK_MOZ_EMBED_FLAG_START) {
			browser->total_requests = 0;
			browser->current_requests = 0;
			browser->progress = 0.0;
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
			gecko_browser_set_progress(browser, progress);
		}
	}
}

static void
gecko_browser_init(GeckoBrowser *browser)
{
	browser->progress = 0.0;

	g_signal_connect(G_OBJECT(browser), "new-window",
					 G_CALLBACK(new_window_cb), NULL);
	g_signal_connect(G_OBJECT(browser), "net-state-all",
					 G_CALLBACK(net_state_cb), NULL);
}
