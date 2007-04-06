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

#ifndef __SUGAR_AUDIO_MANAGER_H__
#define __SUGAR_AUDIO_MANAGER_H__

#include <glib-object.h>

G_BEGIN_DECLS

typedef struct _SugarAudioManager SugarAudioManager;
typedef struct _SugarAudioManagerClass SugarAudioManagerClass;
typedef struct _SugarAudioManagerPrivate SugarAudioManagerPrivate;

#define SUGAR_TYPE_AUDIO_MANAGER	      (sugar_audio_manager_get_type())
#define SUGAR_AUDIO_MANAGER(object)	      (G_TYPE_CHECK_INSTANCE_CAST((object), SUGAR_TYPE_AUDIO_MANAGER, SugarAudioManager))
#define SUGAR_AUDIO_MANAGER_CLASS(klass)      (G_TYPE_CHACK_CLASS_CAST((klass), SUGAR_TYPE_AUDIO_MANAGER, SugarAudioManagerClass))
#define SUGAR_IS_AUDIO_MANAGER(object)	      (G_TYPE_CHECK_INSTANCE_TYPE((object), SUGAR_TYPE_AUDIO_MANAGER))
#define SUGAR_IS_AUDIO_MANAGER_CLASS(klass)   (G_TYPE_CHECK_CLASS_TYPE((klass), SUGAR_TYPE_AUDIO_MANAGER))
#define SUGAR_AUDIO_MANAGER_GET_CLASS(object) (G_TYPE_INSTANCE_GET_CLASS((object), SUGAR_TYPE_AUDIO_MANAGER, SugarAudioManagerClass))

struct _SugarAudioManager {
	GObject base_instance;

	/*< private >*/
	SugarAudioManagerPrivate *priv;
};

struct _SugarAudioManagerClass {
	GObjectClass base_class;
};

GType	 sugar_audio_manager_get_type	(void);
void     sugar_audio_manager_set_volume (SugarAudioManager *manager,
					 int                level);

G_END_DECLS

#endif /* __SUGAR_AUDIO_MANAGER_H__ */
