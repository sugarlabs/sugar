#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include "xulrunner.h"

/* include this first, before NO_IMPORT_PYGOBJECT is defined */
#include <pygobject.h>

void py_sugarbrowser_register_classes (PyObject *d);

extern PyMethodDef py_sugarbrowser_functions[];

DL_EXPORT(void)
init_sugarbrowser(void)
{
    PyObject *m, *d;

    xulrunner_startup();

    init_pygobject ();

    m = Py_InitModule ("_sugarbrowser", py_sugarbrowser_functions);
    d = PyModule_GetDict (m);

    py_sugarbrowser_register_classes (d);
    py_sugarbrowser_add_constants(m, "GTK_MOZ_EMBED_");

    if (PyErr_Occurred ()) {
        Py_FatalError ("can't initialise module _sugarbrowser");
    }
}
