#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

/* include this first, before NO_IMPORT_PYGOBJECT is defined */
#include <pygobject.h>

void py_sugarext_register_classes (PyObject *d);

extern PyMethodDef py_sugarext_functions[];

DL_EXPORT(void)
init_sugarext(void)
{
    PyObject *m, *d;

    init_pygobject ();

    m = Py_InitModule ("_sugarext", py_sugarext_functions);
    d = PyModule_GetDict (m);

    py_sugarext_register_classes (d);

    if (PyErr_Occurred ()) {
        Py_FatalError ("can't initialise module _sugarext");
    }
}
