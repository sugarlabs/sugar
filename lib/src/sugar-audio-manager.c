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

#include <gst/gst.h>
#include <gst/audio/mixerutils.h>
#include <gst/interfaces/mixer.h>
#include <gst/interfaces/propertyprobe.h>

#include "sugar-audio-manager.h"

struct _SugarAudioManagerPrivate
{
	GstMixer *mixer;
	GstMixerTrack *track;
	guint timer_id;
};

G_DEFINE_TYPE(SugarAudioManager, sugar_audio_manager, G_TYPE_OBJECT)

#define SUGAR_AUDIO_MANAGER_GET_PRIVATE(object) (G_TYPE_INSTANCE_GET_PRIVATE ((object), SUGAR_TYPE_AUDIO_MANAGER, SugarAudioManagerPrivate))

/* This is a modified version of code from gnome-control-center */

static gboolean
mixer_close_real(SugarAudioManager *manager)
{
	if (manager->priv->mixer != NULL)
	{
		gst_element_set_state(GST_ELEMENT(manager->priv->mixer), GST_STATE_NULL);
		gst_object_unref(GST_OBJECT(manager->priv->mixer));	    
		g_object_unref(G_OBJECT(manager->priv->track));
		manager->priv->mixer = NULL;
		manager->priv->track = NULL;
	}
	
	manager->priv->timer_id = 0;

	return FALSE;
}

static gboolean
set_mixer_helper(GstMixer *mixer, gpointer user_data)
{
	const GList *tracks;

	tracks = gst_mixer_list_tracks(mixer);

	while (tracks != NULL) {
		GstMixerTrack *track = GST_MIXER_TRACK(tracks->data);

		if (GST_MIXER_TRACK_HAS_FLAG(track, GST_MIXER_TRACK_MASTER)) {
			SugarAudioManager *manager;

			manager = SUGAR_AUDIO_MANAGER(user_data);

			manager->priv->mixer = mixer;
			manager->priv->track = track;

			/* no need to ref the mixer element */
			g_object_ref(manager->priv->track);
			return TRUE;
		}

		tracks = tracks->next;
	}

	return FALSE;
}

static gboolean
mixer_open(SugarAudioManager *manager)
{
	GList *mixer_list;

	if (manager->priv->timer_id != 0) {
		g_source_remove (manager->priv->timer_id);
		manager->priv->timer_id = 0;
		return TRUE;
	}
		
	mixer_list = gst_audio_default_registry_mixer_filter
					(set_mixer_helper, TRUE, manager);

	if (mixer_list == NULL)
		return FALSE;

	/* do not unref the mixer as we keep the ref for manager->priv->mixer */
	g_list_free (mixer_list);

	return TRUE;
}

static void
mixer_close(SugarAudioManager *manager)
{
	manager->priv->timer_id = g_timeout_add (4000, (GSourceFunc)mixer_close_real, manager);
}

void
sugar_audio_manager_set_volume (SugarAudioManager *manager,
				int                level)
{
	gint i, *volumes, volume;
	GstMixerTrack *track;

	if (mixer_open(manager) == FALSE)
		return;

	track = manager->priv->track;
	volume = CLAMP(level, 0, 100);

	/* Rescale the volume from [0, 100] to [track min, track max]. */
	volume = (volume / 100.0) * (track->max_volume - track->min_volume) +
		 track->min_volume;

	volumes = g_new(gint, track->num_channels);
	for (i = 0; i < track->num_channels; ++i)
		volumes[i] = (gint)volume;
	gst_mixer_set_volume(manager->priv->mixer, track, volumes);
	g_free (volumes);
 	
 	mixer_close(manager);
}

static void
sugar_audio_manager_finalize (GObject *object)
{
	SugarAudioManager *manager = SUGAR_AUDIO_MANAGER(object);

	mixer_close_real(manager);

	G_OBJECT_CLASS(sugar_audio_manager_parent_class)->finalize(object);
}

static void
sugar_audio_manager_class_init(SugarAudioManagerClass *klass)
{
	GObjectClass *object_class = G_OBJECT_CLASS(klass);

	gst_init (NULL, NULL);

	object_class->finalize = sugar_audio_manager_finalize;

	g_type_class_add_private(klass, sizeof(SugarAudioManagerPrivate));
}

static void
sugar_audio_manager_init(SugarAudioManager *manager)
{
	manager->priv = SUGAR_AUDIO_MANAGER_GET_PRIVATE(manager);
}


