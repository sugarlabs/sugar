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

typedef struct _SugarBrowser         SugarBrowser;
typedef struct _SugarBrowserClass    SugarBrowserClass;
typedef struct _SugarBrowserEvent    SugarBrowserEvent;
typedef struct _SugarBrowserMetadata SugarBrowserMetadata;

#define SUGAR_TYPE_BROWSER				(sugar_browser_get_type())
#define SUGAR_BROWSER(object)	    	(G_TYPE_CHECK_INSTANCE_CAST((object), SUGAR_TYPE_BROWSER, SugarBrowser))
#define SUGAR_BROWSER_CLASS(klass)		(G_TYPE_CHECK_CLASS_CAST((klass), SUGAR_TYPE_BROWSER, SugarBrowserClass))
#define SUGAR_IS_BROWSER(object)		(G_TYPE_CHECK_INSTANCE_TYPE((object), SUGAR_TYPE_BROWSER))
#define SUGAR_IS_BROWSER_CLASS(klass)	(G_TYPE_CHECK_CLASS_TYPE((klass), SUGAR_TYPE_BROWSER))
#define SUGAR_BROWSER_GET_CLASS(object) (G_TYPE_INSTANCE_GET_CLASS((object), SUGAR_TYPE_BROWSER, SugarBrowserClass))

struct _SugarBrowser {
	GtkMozEmbed base_instance;

    int instance_id;
	int total_requests;
	int current_requests;
	float progress;
	char *address;
	char *title;
	gboolean can_go_back;
	gboolean can_go_forward;
	gboolean loading;

    gboolean (* mouse_click) (SugarBrowser      *browser,
                              SugarBrowserEvent *event);
};

struct _SugarBrowserClass {
	GtkMozEmbedClass base_class;

	SugarBrowser * (* create_window) (SugarBrowser *browser);
};

GType			sugar_browser_get_type		  (void);
int             sugar_browser_get_instance_id (SugarBrowser *browser);
SugarBrowser   *sugar_browser_create_window	  (SugarBrowser *browser);
void			sugar_browser_scroll_pixels   (SugarBrowser *browser,
                            				   int           dx,
                            				   int           dy);
void			sugar_browser_grab_focus	  (SugarBrowser *browser);
gboolean        sugar_browser_save_uri        (SugarBrowser *browser,
                                               const char   *uri,
                                               const char   *filename);
gboolean        sugar_browser_save_document   (SugarBrowser *browser,
                                               const char   *filename);
char           *sugar_browser_get_session     (SugarBrowser *browser);
gboolean        sugar_browser_set_session     (SugarBrowser *browser,
                                               const char   *session);

gboolean        sugar_browser_startup         (const char *profile_path,
                                               const char *profile_name);
void            sugar_browser_shutdown        (void);

#define SUGAR_TYPE_BROWSER_EVENT (sugar_browser_event_get_type())

struct _SugarBrowserEvent {
    int   button;
    char *image_uri;
    char *image_name;
};

GType                sugar_browser_event_get_type (void);
SugarBrowserEvent   *sugar_browser_event_new      (void);
SugarBrowserEvent   *sugar_browser_event_copy     (SugarBrowserEvent *event);
void                 sugar_browser_event_free     (SugarBrowserEvent *event);

#define SUGAR_TYPE_BROWSER_METADATA (sugar_browser_metadata_get_type())

struct _SugarBrowserMetadata {
    char *filename;
};

GType                 sugar_browser_metadata_get_type (void);
SugarBrowserMetadata *sugar_browser_metadata_new      (void);
SugarBrowserMetadata *sugar_browser_metadata_copy     (SugarBrowserMetadata *event);
void                  sugar_browser_metadata_free     (SugarBrowserMetadata *event);

G_END_DECLS

#endif
