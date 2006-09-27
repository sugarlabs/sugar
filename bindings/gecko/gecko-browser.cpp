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
gecko_browser_class_init(GeckoBrowserClass *browser_class)
{
}

GeckoBrowser *
gecko_browser_create_window(GeckoBrowser *browser)
{
	return GECKO_BROWSER_GET_CLASS(browser)->create_window(browser);
}

static void
gecko_browser_new_window_cb(GtkMozEmbed  *embed,
							GtkMozEmbed **newEmbed,
                            guint         chromemask)
{
	GeckoBrowser *browser;

	browser = gecko_browser_create_window(GECKO_BROWSER(embed));

	*newEmbed = GTK_MOZ_EMBED(browser);
}

static void
gecko_browser_init(GeckoBrowser *browser)
{
	g_signal_connect(G_OBJECT(browser), "new-window",
					 G_CALLBACK(gecko_browser_new_window_cb), NULL);
}
