/*
 *  Copyright © 2002 Ricardo Fernádez Pascual
 *  Copyright © 2005 Crispin Flowerday
 *  Copyright © 2005 Christian Persch
 *  Copyright © 2005 Samuel Abels
 *  Copyright (C) 2006, Red Hat, Inc.
 *
 *  This program is free software; you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation; either version 2, or (at your option)
 *  any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with this program; if not, write to the Free Software
 *  Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
 *
 *  $Id: ephy-push-scroller.c,v 1.6 2006/09/13 19:01:24 chpe Exp $
 */

/* this file is based on work of Daniel Erat for galeon 1 */

#include "sugar-push-scroller.h"

#include <gtk/gtkimage.h>
#include <gtk/gtkwindow.h>
#include <gtk/gtkmain.h>

#include <stdlib.h>

#define SUGAR_PUSH_SCROLLER_GET_PRIVATE(object) (G_TYPE_INSTANCE_GET_PRIVATE ((object), SUGAR_TYPE_PUSH_SCROLLER, SugarPushScrollerPrivate))

struct _SugarPushScrollerPrivate
{
	SugarBrowser *browser;
	GdkCursor *cursor;
	guint start_x;
	guint start_y;
	guint active : 1;
};

G_DEFINE_TYPE(SugarPushScroller, sugar_push_scroller, G_TYPE_OBJECT)

/* private functions */

static gboolean
sugar_push_scroller_motion_cb(GtkWidget         *widget,
			      			  GdkEventMotion    *event,
			      			  SugarPushScroller *scroller)
{
	SugarPushScrollerPrivate *priv = scroller->priv;
	int x_dist, x_dist_abs, y_dist, y_dist_abs;

	if (!priv->active) {
		return FALSE;
	}

	/* get distance between last known cursor position and cursor */
	x_dist = priv->start_x - event->x_root;
	x_dist_abs = abs(x_dist);
	y_dist = priv->start_y - event->y_root;
	y_dist_abs = abs(y_dist);

	/* scroll */
	sugar_browser_scroll_pixels(priv->browser, x_dist, y_dist);

	priv->start_x = event->x_root;
	priv->start_y = event->y_root;

	return TRUE;
}

/* public functions */

void
sugar_push_scroller_start (SugarPushScroller *scroller,
			  			   SugarBrowser      *browser,
			  			   int                x,
			  			   int				  y)
{
	SugarPushScrollerPrivate *priv = scroller->priv;
	GtkWidget *widget, *window;
	guint32 timestamp;

	g_return_if_fail (browser != NULL);

	if (priv->active)
		return;

	if (gdk_pointer_is_grabbed ())
		return;

	priv->active = TRUE;

	/* FIXME is this good enough? */
	timestamp = gtk_get_current_event_time();

	g_object_ref (scroller);

	priv->browser = browser;

	window = gtk_widget_get_toplevel(GTK_WIDGET(browser));
	g_object_ref (window);

	/* set positions */
	priv->start_x = x;
	priv->start_y = y;

	g_signal_connect(window, "motion-notify-event",
			         G_CALLBACK (sugar_push_scroller_motion_cb), scroller);

	/* grab the pointer */
	widget = GTK_WIDGET(window);
	gtk_grab_add(widget);
	if (gdk_pointer_grab(widget->window, FALSE,
			      GDK_POINTER_MOTION_MASK |
			      GDK_BUTTON_PRESS_MASK |
			      GDK_BUTTON_RELEASE_MASK,
			      NULL, priv->cursor, timestamp) != GDK_GRAB_SUCCESS) {
		sugar_push_scroller_stop(scroller, timestamp);
		return;
	}
}

void
sugar_push_scroller_stop (SugarPushScroller *scroller,
			 			  guint32            timestamp)
{
	SugarPushScrollerPrivate *priv = scroller->priv;
	GtkWidget *widget, *window;

	if (priv->active == FALSE)
		return;

	window = gtk_widget_get_toplevel(GTK_WIDGET(priv->browser));

	/* disconnect the signals before ungrabbing! */
	g_signal_handlers_disconnect_matched (window,
					      G_SIGNAL_MATCH_DATA, 0, 0, 
					      NULL, NULL, scroller);

	/* ungrab the pointer if it's grabbed */
	if (gdk_pointer_is_grabbed())
	{
		gdk_pointer_ungrab(timestamp);
	}

	gdk_keyboard_ungrab(timestamp);

	widget = GTK_WIDGET(window);
	gtk_grab_remove(widget);

	g_object_unref(window);

	priv->browser = NULL;
	priv->active = FALSE;

	g_object_unref(scroller);
}

/* class implementation */

static void 
sugar_push_scroller_init (SugarPushScroller *scroller)
{
	SugarPushScrollerPrivate *priv;
	priv = scroller->priv = SUGAR_PUSH_SCROLLER_GET_PRIVATE(scroller);
	priv->active = FALSE;
	priv->cursor = gdk_cursor_new(GDK_FLEUR);
}

static void
sugar_push_scroller_finalize (GObject *object)
{
	SugarPushScroller *scroller = SUGAR_PUSH_SCROLLER(object);
	SugarPushScrollerPrivate *priv = scroller->priv;

	gdk_cursor_unref(priv->cursor);

	G_OBJECT_CLASS(sugar_push_scroller_parent_class)->finalize(object);
}

static void
sugar_push_scroller_class_init (SugarPushScrollerClass *klass)
{
	GObjectClass *object_class = G_OBJECT_CLASS(klass);

	object_class->finalize = sugar_push_scroller_finalize;

	g_type_class_add_private(klass, sizeof (SugarPushScrollerPrivate));
}
