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

#include <X11/X.h>
#include <gdk/gdkscreen.h>
#include <gdk/gdkx.h>
#include <gdk/gdk.h>

#include "sugar-key-grabber.h"
#include "eggaccelerators.h"

/* we exclude shift, GDK_CONTROL_MASK and GDK_MOD1_MASK since we know what
   these modifiers mean
   these are the mods whose combinations are bound by the keygrabbing code */
#define IGNORED_MODS (0x2000 /*Xkb modifier*/ | GDK_LOCK_MASK  | \
        GDK_MOD2_MASK | GDK_MOD3_MASK | GDK_MOD4_MASK | GDK_MOD5_MASK)
/* these are the ones we actually use for global keys, we always only check
 * for these set */
#define USED_MODS (GDK_SHIFT_MASK | GDK_CONTROL_MASK | GDK_MOD1_MASK)

struct _SugarKeyGrabber {
	GObject base_instance;

	GdkWindow *root;
	GList *keys;
};

struct _SugarKeyGrabberClass {
	GObjectClass base_class;

	void (* key_pressed) (SugarKeyGrabber *grabber,
						  const char      *key);
};

enum {
	KEY_PRESSED,
	N_SIGNALS
};

typedef struct {
  char *key;
  guint keysym;
  guint state;
  guint keycode;
} Key;

G_DEFINE_TYPE(SugarKeyGrabber, sugar_key_grabber, G_TYPE_OBJECT)

static guint signals[N_SIGNALS];

static void
free_key_info(Key *key_info)
{
	g_free(key_info->key);
	g_free(key_info);
}

static void
sugar_key_grabber_dispose (GObject *object)
{
	SugarKeyGrabber *grabber = SUGAR_KEY_GRABBER(object);

	if (grabber->keys) {
		g_list_foreach(grabber->keys, (GFunc)free_key_info, NULL);
		g_list_free(grabber->keys);
		grabber->keys = NULL;
	}
}

static void
sugar_key_grabber_class_init(SugarKeyGrabberClass *grabber_class)
{
	GObjectClass *g_object_class = G_OBJECT_CLASS (grabber_class);

	g_object_class->dispose = sugar_key_grabber_dispose;

	signals[KEY_PRESSED] = g_signal_new ("key-pressed",
                         G_TYPE_FROM_CLASS (grabber_class),
                         G_SIGNAL_RUN_LAST | G_SIGNAL_ACTION,
                         G_STRUCT_OFFSET (SugarKeyGrabberClass, key_pressed),
                         NULL, NULL,
                         g_cclosure_marshal_VOID__STRING,
                         G_TYPE_NONE, 1,
                         G_TYPE_STRING);
}

static GdkFilterReturn
filter_events(GdkXEvent *xevent, GdkEvent *event, gpointer data)
{
	SugarKeyGrabber *grabber = (SugarKeyGrabber *)data;
	XEvent *xev = (XEvent *)xevent;

	if (xev->type == KeyPress) {
		GList *l;
		guint keycode, state;

		keycode = xev->xkey.keycode;
		state = xev->xkey.state;

		for (l = grabber->keys; l != NULL; l = l->next) {
			Key *keyinfo = (Key *)l->data;
			if (keyinfo->keycode == keycode &&
			    (state & USED_MODS) == keyinfo->state) {
				g_signal_emit (grabber, signals[KEY_PRESSED],
							   0, keyinfo->key);
				return GDK_FILTER_REMOVE;
			}
		}
	}

	return GDK_FILTER_CONTINUE;
}

static void
sugar_key_grabber_init(SugarKeyGrabber *grabber)
{
	GdkScreen *screen;

	screen = gdk_screen_get_default();
	grabber->root = gdk_screen_get_root_window(screen);
	grabber->keys = NULL;

	gdk_window_add_filter(grabber->root, filter_events, grabber);
}

/* grab_key and grab_key_real are from 
 * gnome-control-center/gnome-settings-daemon/gnome-settings-multimedia-keys.c
 */

static gboolean
grab_key_real (Key *key, GdkWindow *root, gboolean grab, int result)
{
        gdk_error_trap_push ();
        if (grab)
                XGrabKey (GDK_DISPLAY(), key->keycode, (result | key->state),
                                GDK_WINDOW_XID (root), True, GrabModeAsync, GrabModeAsync);
        else
                XUngrabKey(GDK_DISPLAY(), key->keycode, (result | key->state),
                                GDK_WINDOW_XID (root));
        gdk_flush ();

        gdk_error_trap_pop ();

        return TRUE;
}

#define N_BITS 32
static void
grab_key (SugarKeyGrabber *grabber, Key *key, gboolean grab)
{
        int indexes[N_BITS];/*indexes of bits we need to flip*/
        int i, bit, bits_set_cnt;
        int uppervalue;
        guint mask_to_traverse = IGNORED_MODS & ~ key->state;

        bit = 0;
        for (i = 0; i < N_BITS; i++) {
                if (mask_to_traverse & (1<<i))
                        indexes[bit++]=i;
        }

        bits_set_cnt = bit;

        uppervalue = 1<<bits_set_cnt;
        for (i = 0; i < uppervalue; i++) {
                int j, result = 0;

                for (j = 0; j < bits_set_cnt; j++) {
                        if (i & (1<<j))
                                result |= (1<<indexes[j]);
                }

                if (grab_key_real (key, grabber->root, grab, result) == FALSE)
                        return;
        }
}

void
sugar_key_grabber_grab(SugarKeyGrabber *grabber, const char *key)
{
	Key *keyinfo;

	keyinfo = g_new0 (Key, 1);
	keyinfo->key = g_strdup(key);
	egg_accelerator_parse_virtual (key, &keyinfo->keysym,
								   &keyinfo->keycode, &keyinfo->state);

	grab_key(grabber, keyinfo, TRUE);

	grabber->keys = g_list_append(grabber->keys, keyinfo);	
}
