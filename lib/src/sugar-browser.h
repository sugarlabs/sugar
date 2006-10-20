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

#ifndef __SUGAR_BROWSER_H__
#define __SUGAR_BROWSER_H__

#include <gtkmozembed.h>

G_BEGIN_DECLS

typedef struct _SugarBrowser SugarBrowser;
typedef struct _SugarBrowserClass SugarBrowserClass;

#define SUGAR_TYPE_BROWSER				(sugar_browser_get_type())
#define SUGAR_BROWSER(object)	    	(G_TYPE_CHECK_INSTANCE_CAST((object), SUGAR_TYPE_BROWSER, SugarBrowser))
#define SUGAR_BROWSER_CLASS(klass)		(G_TYPE_CHECK_CLASS_CAST((klass), SUGAR_TYPE_BROWSER, SugarBrowserClass))
#define SUGAR_IS_BROWSER(object)		(G_TYPE_CHECK_INSTANCE_TYPE((object), SUGAR_TYPE_BROWSER))
#define SUGAR_IS_BROWSER_CLASS(klass)	(G_TYPE_CHECK_CLASS_TYPE((klass), SUGAR_TYPE_BROWSER))
#define SUGAR_BROWSER_GET_CLASS(object) (G_TYPE_INSTANCE_GET_CLASS((object), SUGAR_TYPE_BROWSER, SugarBrowserClass))

struct _SugarBrowser {
	GtkMozEmbed base_instance;

	int total_requests;
	int current_requests;
	float progress;
	char *address;
	char *title;
	gboolean can_go_back;
	gboolean can_go_forward;
	gboolean loading;
};

struct _SugarBrowserClass {
	GtkMozEmbedClass base_class;

	SugarBrowser * (* create_window) (SugarBrowser *browser);
};

GType			sugar_browser_get_type		(void);
void			sugar_browser_startup		(void);
SugarBrowser   *sugar_browser_create_window	(SugarBrowser *browser);
void			sugar_browser_scroll_pixels (SugarBrowser *browser,
                            				 int           dx,
                            				 int           dy);

G_END_DECLS

#endif
