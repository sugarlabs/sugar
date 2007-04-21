#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

/* include this first, before NO_IMPORT_PYGOBJECT is defined */
#include <pygobject.h>

void py_extensions_register_classes (PyObject *d);

extern PyMethodDef py_extensions_functions[];

DL_EXPORT(void)
init_extensions(void)
{
    PyObject *m, *d;

    init_pygobject ();

    m = Py_InitModule ("_extensions", py_extensions_functions);
    d = PyModule_GetDict (m);

    py_extensions_register_classes (d);

    if (PyErr_Occurred ()) {
        Py_FatalError ("can't initialise module _sugar");
    }
}
