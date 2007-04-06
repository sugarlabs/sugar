#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

/* include this first, before NO_IMPORT_PYGOBJECT is defined */
#include <pygobject.h>

void pyextensions_register_classes (PyObject *d);

extern PyMethodDef pyextensions_functions[];

DL_EXPORT(void)
initextensions(void)
{
    PyObject *m, *d;

    init_pygobject ();

    m = Py_InitModule ("extensions", pyextensions_functions);
    d = PyModule_GetDict (m);

    pyextensions_register_classes (d);

    if (PyErr_Occurred ()) {
        Py_FatalError ("can't initialise module _sugar");
    }
}
