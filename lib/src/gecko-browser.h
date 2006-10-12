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

#ifndef __GECKO_BROWSER_H__
#define __GECKO_BROWSER_H__

#include <gtkmozembed.h>

G_BEGIN_DECLS

typedef struct _GeckoBrowser GeckoBrowser;
typedef struct _GeckoBrowserClass GeckoBrowserClass;

#define GECKO_TYPE_BROWSER				(gecko_browser_get_type())
#define GECKO_BROWSER(object)	    	(G_TYPE_CHECK_INSTANCE_CAST((object), GECKO_TYPE_BROWSER, GeckoBrowser))
#define GECKO_BROWSER_CLASS(klass)		(G_TYPE_CHECK_CLASS_CAST((klass), GECKO_TYPE_BROWSER, GeckoBrowserClass))
#define GECKO_IS_BROWSER(object)		(G_TYPE_CHECK_INSTANCE_TYPE((object), GECKO_TYPE_BROWSER))
#define GECKO_IS_BROWSER_CLASS(klass)	(G_TYPE_CHECK_CLASS_TYPE((klass), GECKO_TYPE_BROWSER))
#define GECKO_BROWSER_GET_CLASS(object) (G_TYPE_INSTANCE_GET_CLASS((object), GECKO_TYPE_BROWSER, GeckoBrowserClass))

struct _GeckoBrowser {
	GtkMozEmbed base_instance;

	int total_requests;
	int current_requests;
	float progress;
};

struct _GeckoBrowserClass {
	GtkMozEmbedClass base_class;

	GeckoBrowser * (* create_window) (GeckoBrowser *browser);
};

GType			gecko_browser_get_type		(void);
void			gecko_browser_startup		(void);
GeckoBrowser   *gecko_browser_new 			(void);
GeckoBrowser   *gecko_browser_create_window	(GeckoBrowser *browser);

G_END_DECLS

#endif
