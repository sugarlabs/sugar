/*
 * Copyright (C) 2006-2007, Red Hat, Inc.
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

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

/* include this first, before NO_IMPORT_PYGOBJECT is defined */
#include <pygobject.h>

extern PyMethodDef py_sugaruiext_functions[];

void py_sugaruiext_register_classes (PyObject *d);

DL_EXPORT(void)
init_sugaruiext(void)
{
    PyObject *m, *d;

    init_pygobject ();

    m = Py_InitModule ("_sugaruiext", py_sugaruiext_functions);
    d = PyModule_GetDict (m);

    py_sugaruiext_register_classes (d);

    if (PyErr_Occurred ()) {
        Py_FatalError ("can't initialise module _sugaruiext");
    }
}
