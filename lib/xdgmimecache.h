/* -*- mode: C; c-file-style: "gnu" -*- */
/* xdgmimecache.h: Private file.  Datastructure for mmapped caches.
 *
 * More info can be found at http://www.freedesktop.org/standards/
 *
 * Copyright (C) 2005  Matthias Clasen <mclasen@redhat.com>
 *
 * Licensed under the Academic Free License version 2.0
 * Or under the following terms:
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	 See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library; if not, write to the
 * Free Software Foundation, Inc., 59 Temple Place - Suite 330,
 * Boston, MA 02111-1307, USA.
 */

#ifndef __XDG_MIME_CACHE_H__
#define __XDG_MIME_CACHE_H__

#include "xdgmime.h"

typedef struct _XdgMimeCache XdgMimeCache;

#ifdef XDG_PREFIX
#define _xdg_mime_cache_new_from_file        XDG_ENTRY(cache_new_from_file)
#define _xdg_mime_cache_ref                  XDG_ENTRY(cache_ref)
#define _xdg_mime_cache_unref                XDG_ENTRY(cache_unref)
#endif

extern XdgMimeCache **_caches;

XdgMimeCache *_xdg_mime_cache_new_from_file (const char   *file_name);
XdgMimeCache *_xdg_mime_cache_ref           (XdgMimeCache *cache);
void          _xdg_mime_cache_unref         (XdgMimeCache *cache);


const char  *_xdg_mime_cache_get_mime_type_for_data       (const void *data,
		 				           size_t      len);
const char  *_xdg_mime_cache_get_mime_type_for_file       (const char  *file_name,
							   struct stat *statbuf);
const char  *_xdg_mime_cache_get_mime_type_from_file_name (const char *file_name);
int          _xdg_mime_cache_is_valid_mime_type           (const char *mime_type);
int          _xdg_mime_cache_mime_type_equal              (const char *mime_a,
						           const char *mime_b);
int          _xdg_mime_cache_media_type_equal             (const char *mime_a,
							   const char *mime_b);
int          _xdg_mime_cache_mime_type_subclass           (const char *mime_a,
							   const char *mime_b);
char       **_xdg_mime_cache_list_mime_parents		  (const char *mime);
const char  *_xdg_mime_cache_unalias_mime_type            (const char *mime);
int          _xdg_mime_cache_get_max_buffer_extents       (void);

#endif /* __XDG_MIME_CACHE_H__ */
