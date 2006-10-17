/*
 *  Copyright © 2002 Ricardo Fernádez Pascual
 *  Copyright © 2005 Crispin Flowerday
 *  Copyright © 2005 Christian Persch
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
 *  $Id: ephy-push-scroller.h,v 1.2 2006/09/13 19:01:24 chpe Exp $
 */

#ifndef SUGAR_PUSH_SCROLLER_H
#define SUGAR_PUSH_SCROLLER_H

#include <glib-object.h>
#include <gtk/gtkwidget.h>

#include "sugar-browser.h"

G_BEGIN_DECLS

#define SUGAR_TYPE_PUSH_SCROLLER		 	(sugar_push_scroller_get_type())
#define SUGAR_PUSH_SCROLLER(object)		 	(G_TYPE_CHECK_INSTANCE_CAST((object), SUGAR_TYPE_PUSH_SCROLLER, SugarPushScroller))
#define SUGAR_PUSH_SCROLLER_CLASS(klass) 	(G_TYPE_CHECK_CLASS_CAST((klass), SUGAR_TYPE_PUSH_SCROLLER, SugarPushScrollerClass))
#define SUGAR_IS_PUSH_SCROLLER(object)	   	(G_TYPE_CHECK_INSTANCE_TYPE((object), SUGAR_TYPE_PUSH_SCROLLER))
#define SUGAR_IS_PUSH_SCROLLER_CLASS(klass)	(G_TYPE_CHECK_CLASS_TYPE((klass), SUGAR_TYPE_PUSH_SCROLLER))
#define SUGAR_PUSH_SCROLLER_GET_CLASS(obj)	(G_TYPE_INSTANCE_GET_CLASS((obj), SUGAR_TYPE_PUSH_SCROLLER, SugarPushScrollerClass))

typedef struct _SugarPushScrollerClass SugarPushScrollerClass;
typedef struct _SugarPushScroller SugarPushScroller;
typedef struct _SugarPushScrollerPrivate SugarPushScrollerPrivate;

struct _SugarPushScrollerClass {
	GObjectClass parent_class;
};

struct _SugarPushScroller {
	GObject parent_object;

	/*< private >*/
	SugarPushScrollerPrivate *priv;
};

GType				sugar_push_scroller_get_type	  (void);
void				sugar_push_scroller_start	 	  (SugarPushScroller *scroller,
													   SugarBrowser      *browser,
							  						   int                x,
							  						   int                y);
void				sugar_push_scroller_stop		  (SugarPushScroller *scroller,
							  						   guint32            timestamp);

G_END_DECLS

#endif
