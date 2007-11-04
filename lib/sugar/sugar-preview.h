/*
 * Copyright (C) 2007, Red Hat, Inc.
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

#ifndef __SUGAR_PREVIEW_H__
#define __SUGAR_PREVIEW_H__

#include <gdk/gdkdrawable.h>

G_BEGIN_DECLS

typedef struct _SugarPreview SugarPreview;
typedef struct _SugarPreviewClass SugarPreviewClass;

#define SUGAR_TYPE_PREVIEW			    (sugar_preview_get_type())
#define SUGAR_PREVIEW(object)	        (G_TYPE_CHECK_INSTANCE_CAST((object), SUGAR_TYPE_PREVIEW, SugarPreview))
#define SUGAR_PREVIEW_CLASS(klass)	    (G_TYPE_CHACK_CLASS_CAST((klass), SUGAR_TYPE_PREVIEW, SugarPreviewClass))
#define SUGAR_IS_PREVIEW(object)	    (G_TYPE_CHECK_INSTANCE_TYPE((object), SUGAR_TYPE_PREVIEW))
#define SUGAR_IS_PREVIEW_CLASS(klass)   (G_TYPE_CHECK_CLASS_TYPE((klass), SUGAR_TYPE_PREVIEW))
#define SUGAR_PREVIEW_GET_CLASS(object) (G_TYPE_INSTANCE_GET_CLASS((object), SUGAR_TYPE_PREVIEW, SugarPreviewClass))

struct _SugarPreview {
    GObject base_instance;

    GdkImage *image;
    int width;
    int height;
};

struct _SugarPreviewClass {
	GObjectClass base_class;
};

GType	   sugar_preview_get_type        (void);
void       sugar_preview_take_screenshot (SugarPreview *preview,
                                          GdkDrawable  *drawable);
void       sugar_preview_set_size        (SugarPreview *preview,
                                          int width,
                                          int height);
GdkPixbuf *sugar_preview_get_pixbuf      (SugarPreview *preview);
void       sugar_preview_clear           (SugarPreview *preview);

G_END_DECLS

#endif /* __SUGAR_PREVIEW_H__ */
