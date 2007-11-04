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

#include <gdk/gdkx.h>
#include <gtk/gtkwindow.h>

#include "sugar-preview.h"

static void sugar_preview_class_init (SugarPreviewClass *menu_class);
static void sugar_preview_init       (SugarPreview *menu);

G_DEFINE_TYPE(SugarPreview, sugar_preview, G_TYPE_OBJECT)

gboolean
sugar_preview_save(SugarPreview *preview, const char *file_name)
{
    GdkPixbuf *pixbuf;

    if (preview->image != NULL) {
        return FALSE;
    }

    pixbuf = gdk_pixbuf_get_from_image(NULL, preview->image, NULL,
                                       0, 0, 0, 0,
                                       preview->image->width,
                                       preview->image->height);

    gdk_pixbuf_save(pixbuf, file_name, "png", NULL);

    if (preview->image != NULL) {
        g_object_unref(G_OBJECT(preview->image));
        preview->image = NULL;
    }

    return TRUE;
}

void
sugar_preview_take_screenshot(SugarPreview *preview, GdkDrawable *drawable)
{
    GdkScreen *screen;
    GdkVisual *visual;
    GdkColormap *colormap;
    gint width, height;

    gdk_drawable_get_size(drawable, &width, &height);

    screen = gdk_drawable_get_screen(drawable);
    visual = gdk_drawable_get_visual(drawable);
    colormap = gdk_drawable_get_colormap(drawable);

    if (preview->image != NULL) {
        g_object_unref(G_OBJECT(preview->image));
    }

    preview->image = gdk_image_new(GDK_IMAGE_SHARED, visual, width, height);
    gdk_image_set_colormap(preview->image, colormap);

    XShmGetImage(GDK_SCREEN_XDISPLAY(screen),
                 GDK_DRAWABLE_XID(drawable),
                 gdk_x11_image_get_ximage(preview->image),
                 0, 0, AllPlanes, ZPixmap);
}

static void
sugar_preview_dispose (GObject *object)
{
    SugarPreview *preview = SUGAR_PREVIEW(object);

    if (preview->image != NULL) {
        g_object_unref(G_OBJECT(preview->image));
        preview->image = NULL;
    }
}


static void
sugar_preview_class_init(SugarPreviewClass *preview_class)
{
    GObjectClass *g_object_class = G_OBJECT_CLASS (preview_class);

    g_object_class->dispose = sugar_preview_dispose;
}

static void
sugar_preview_init(SugarPreview *preview)
{
    preview->image = NULL;
}
