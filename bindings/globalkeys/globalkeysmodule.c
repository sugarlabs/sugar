#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

/* include this first, before NO_IMPORT_PYGOBJECT is defined */
#include <pygobject.h>

void pyglobalkeys_register_classes (PyObject *d);

extern PyMethodDef pyglobalkeys_functions[];

DL_EXPORT(void)
initglobalkeys(void)
{
    PyObject *m, *d;

    init_pygobject ();

    m = Py_InitModule ("globalkeys", pyglobalkeys_functions);
    d = PyModule_GetDict (m);

    pyglobalkeys_register_classes (d);

    if (PyErr_Occurred ()) {
        Py_FatalError ("can't initialise module globalkeys");
    }
}
