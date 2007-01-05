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

#include "sugar-audio-manager.h"

G_DEFINE_TYPE(SugarAudioManager, sugar_audio_manager, G_TYPE_OBJECT)

static void
sugar_audio_manager_class_init(SugarAudioManagerClass *grabber_class)
{
	GObjectClass *g_object_class = G_OBJECT_CLASS (grabber_class);
}

static void
sugar_audio_manager_init(SugarAudioManager *grabber)
{
}

void
sugar_audio_manager_set_volume (SugarAudioManager *manager,
				int                level)
{
}
