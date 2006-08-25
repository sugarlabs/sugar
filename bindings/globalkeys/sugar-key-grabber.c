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

#include "sugar-key-grabber.h"

/* we exclude shift, GDK_CONTROL_MASK and GDK_MOD1_MASK since we know what
   these modifiers mean
   these are the mods whose combinations are bound by the keygrabbing code */
#define IGNORED_MODS (0x2000 /*Xkb modifier*/ | GDK_LOCK_MASK  | \
        GDK_MOD2_MASK | GDK_MOD3_MASK | GDK_MOD4_MASK | GDK_MOD5_MASK)

struct _SugarKeyGrabber {
	GObject base_instance;

	GdkWindow *root;
};

struct _SugarKeyGrabberClass {
	GObjectClass base_class;
};

G_DEFINE_TYPE(SugarKeyGrabber, sugar_key_grabber, G_TYPE_OBJECT)

static void
sugar_key_grabber_class_init(SugarKeyGrabberClass *key_grabber_class)
{ 
}

static GdkFilterReturn
filter_events(GdkXEvent *xevent, GdkEvent *event, gpointer data)
{
    SugarKeyGrabber *grabber = (SugarKeyGrabber *)data;
	XEvent *xev = (XEvent *)xevent;
	XAnyEvent *xanyev = (XAnyEvent *)xevent;
	guint keycode, state;
	int i;

	keycode = xev->xkey.keycode;
	state = xev->xkey.state;

	g_print("KeyCode %d", keycode);
}

static void
sugar_key_grabber_init(SugarKeyGrabber *grabber)
{
	GdkScreen *screen;

	screen = gdk_screen_get_default();
	grabber->root = gdk_screen_get_root_window(screen);

	gdk_window_add_filter(grabber->root, filter_events, grabber);
}


/* inspired from all_combinations from gnome-panel/gnome-panel/global-keys.c */
#define N_BITS 32
static int
get_modifier(guint state)
{
	int indexes[N_BITS];/*indexes of bits we need to flip*/
	int i, bit, bits_set_cnt;
	int uppervalue;
	int result = 0;
	guint mask_to_traverse = IGNORED_MODS & ~ state;

	bit = 0;
	for (i = 0; i < N_BITS; i++) {
		if (mask_to_traverse & (1<<i))
			indexes[bit++]=i;
	}

	bits_set_cnt = bit;

	uppervalue = 1<<bits_set_cnt;
	for (i = 0; i < uppervalue; i++) {
		int j;

		for (j = 0; j < bits_set_cnt; j++) {
			if (i & (1<<j))
				result |= (1<<indexes[j]);
		}

	}

	return (result | state);
}

void
sugar_key_grabber_grab(SugarKeyGrabber *grabber, const char *key)
{
	guint keysym;
	guint state;
	guint keycode;

	gdk_error_trap_push ();

	egg_accelerator_parse_virtual (key, &keysym, &keycode, &state);

	XGrabKey (GDK_DISPLAY(), keycode, get_modifier(state),
			  GDK_WINDOW_XID (grabber->root), True,
			  GrabModeAsync, GrabModeAsync);
	
	gdk_flush ();

	gdk_error_trap_pop ();
}
