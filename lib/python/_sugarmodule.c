#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include "xulrunner.h"

/* include this first, before NO_IMPORT_PYGOBJECT is defined */
#include <pygobject.h>

#include <pycairo.h>
Pycairo_CAPI_t *Pycairo_CAPI;

void py_sugar_register_classes (PyObject *d);

extern PyMethodDef py_sugar_functions[];

DL_EXPORT(void)
init_sugar(void)
{
    PyObject *m, *d;

    xulrunner_startup();

    init_pygobject ();

    Pycairo_IMPORT;

    m = Py_InitModule ("_sugar", py_sugar_functions);
    d = PyModule_GetDict (m);

    py_sugar_register_classes (d);

    if (PyErr_Occurred ()) {
        Py_FatalError ("can't initialise module _sugar");
    }
}
