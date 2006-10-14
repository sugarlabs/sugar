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

#ifndef __SUGAR_ADDRESS_ENTRY_H__
#define __SUGAR_ADDRESS_ENTRY_H__

#include <glib-object.h>

G_BEGIN_DECLS

typedef struct _SugarAddressEntry SugarAddressEntry;
typedef struct _SugarAddressEntryClass SugarAddressEntryClass;
typedef struct _SugarAddressEntryPrivate SugarAddressEntryPrivate;

#define SUGAR_TYPE_ADDRESS_ENTRY		      (sugar_address_entry_get_type())
#define SUGAR_ADDRESS_ENTRY(object)	          (G_TYPE_CHECK_INSTANCE_CAST((object), SUGAR_TYPE_ADDRESS_ENTRY, SugarAddressEntry))
#define SUGAR_ADDRESS_ENTRY_CLASS(klass)      (G_TYPE_CHACK_CLASS_CAST((klass), SUGAR_TYPE_ADDRESS_ENTRY, SugarAddressEntryClass))
#define SUGAR_IS_ADDRESS_ENTRY(object)	      (G_TYPE_CHECK_INSTANCE_TYPE((object), SUGAR_TYPE_ADDRESS_ENTRY))
#define SUGAR_IS_ADDRESS_ENTRY_CLASS(klass)   (G_TYPE_CHECK_CLASS_TYPE((klass), SUGAR_TYPE_ADDRESS_ENTRY))
#define SUGAR_ADDRESS_ENTRY_GET_CLASS(object) (G_TYPE_INSTANCE_GET_CLASS((object), SUGAR_TYPE_ADDRESS_ENTRY, SugarAddressEntryClass))

struct _SugarAddressEntry {
	GtkEntry base_instance;

	float progress;
};

struct _SugarAddressEntryClass {
	GtkEntryClass base_class;
};

GType sugar_address_entry_get_type (void);

G_END_DECLS

#endif /* __SUGAR_ADDRESS_ENTRY_H__ */
