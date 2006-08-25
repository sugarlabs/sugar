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

#include "sugar-key-grabber.h"

struct _SugarKeyGrabber {
	gpointer dummy;
};

struct _SugarKeyGrabberClass {
	GObjectClass base_class;
};

G_DEFINE_TYPE(SugarKeyGrabber, sugar_key_grabber, G_TYPE_OBJECT)

static void
sugar_key_grabber_class_init (SugarKeyGrabberClass *key_grabber_class)
{ 
}

static void
sugar_key_grabber_init (SugarKeyGrabber *key_grabber)
{
}
