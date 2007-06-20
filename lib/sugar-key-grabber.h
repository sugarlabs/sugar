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

#ifndef __SUGAR_KEY_GRABBER_H__
#define __SUGAR_KEY_GRABBER_H__

#include <glib-object.h>
#include <gdk/gdkwindow.h>

G_BEGIN_DECLS

typedef struct _SugarKeyGrabber SugarKeyGrabber;
typedef struct _SugarKeyGrabberClass SugarKeyGrabberClass;
typedef struct _SugarKeyGrabberPrivate SugarKeyGrabberPrivate;

#define SUGAR_TYPE_KEY_GRABBER			(sugar_key_grabber_get_type())
#define SUGAR_KEY_GRABBER(object)	    (G_TYPE_CHECK_INSTANCE_CAST((object), SUGAR_TYPE_KEY_GRABBER, SugarKeyGrabber))
#define SUGAR_KEY_GRABBER_CLASS(klass)	    (G_TYPE_CHACK_CLASS_CAST((klass), SUGAR_TYPE_KEY_GRABBER, SugarKeyGrabberClass))
#define SUGAR_IS_KEY_GRABBER(object)	    (G_TYPE_CHECK_INSTANCE_TYPE((object), SUGAR_TYPE_KEY_GRABBER))
#define SUGAR_IS_KEYGRABBER_CLASS(klass)    (G_TYPE_CHECK_CLASS_TYPE((klass), SUGAR_TYPE_KEY_GRABBER))
#define SUGAR_KEY_GRABBER_GET_CLASS(object) (G_TYPE_INSTANCE_GET_CLASS((object), SUGAR_TYPE_KEY_GRABBER, SugarKeyGrabberClass))

struct _SugarKeyGrabber {
	GObject base_instance;

	GdkWindow *root;
	GList *keys;
};

struct _SugarKeyGrabberClass {
	GObjectClass base_class;

	gboolean (* key_pressed)  (SugarKeyGrabber *grabber,
							   guint            keycode,
							   guint            state);
	gboolean (* key_released) (SugarKeyGrabber *grabber,
							   guint            keycode,
							   guint            state);
};

GType	 sugar_key_grabber_get_type	(void);
void     sugar_key_grabber_grab		(SugarKeyGrabber *grabber,
									 const char	     *key);
char    *sugar_key_grabber_get_key  (SugarKeyGrabber *grabber,
									 guint            keycode,
									 guint            state);

G_END_DECLS

#endif /* __SUGAR_KEY_GRABBER_H__ */
