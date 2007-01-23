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

#include <string.h>

#ifdef HAVE_GECKO_1_9
#include "gtkmozembed_glue.cpp"
#endif

extern "C" int
xulrunner_startup(void)
{
#ifdef HAVE_GECKO_1_9

    static const GREVersionRange greVersion = {
        "1.9a", PR_TRUE,
        "2", PR_TRUE
    };

    char xpcomPath[PATH_MAX];

    nsresult rv = GRE_GetGREPathWithProperties(&greVersion, 1, nsnull, 0,
                                               xpcomPath, sizeof(xpcomPath));
    if (NS_FAILED(rv)) {
        fprintf(stderr, "Couldn't find a compatible GRE.\n");
        return 1;
    }

    rv = XPCOMGlueStartup(xpcomPath);
    if (NS_FAILED(rv)) {
        fprintf(stderr, "Couldn't start XPCOM.");
        return 1;
    }

    rv = GTKEmbedGlueStartup();
    if (NS_FAILED(rv)) {
        fprintf(stderr, "Couldn't find GTKMozEmbed symbols.");
        return 1;
    }

    char *lastSlash = strrchr(xpcomPath, '/');
    if (lastSlash)
        *lastSlash = '\0';

    gtk_moz_embed_set_path(xpcomPath);
#endif
}
