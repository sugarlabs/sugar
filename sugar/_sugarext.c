/* -- THIS FILE IS GENERATED - DO NOT EDIT *//* -*- Mode: C; c-basic-offset: 4 -*- */

#include <Python.h>



#line 4 "_sugarext.override"
#include <Python.h>

#include "pygobject.h"
#include "sugar-address-entry.h"
#include "sugar-x11-util.h"
#include "xdgmime.h"

#include <pygtk/pygtk.h>
#include <glib.h>

#line 19 "_sugarext.c"


/* ---------- types from other modules ---------- */
static PyTypeObject *_PyGtkEntry_Type;
#define PyGtkEntry_Type (*_PyGtkEntry_Type)
static PyTypeObject *_PyGdkWindow_Type;
#define PyGdkWindow_Type (*_PyGdkWindow_Type)


/* ---------- forward type declarations ---------- */
PyTypeObject G_GNUC_INTERNAL PySugarAddressEntry_Type;

#line 32 "_sugarext.c"



/* ----------- SugarAddressEntry ----------- */

PyTypeObject G_GNUC_INTERNAL PySugarAddressEntry_Type = {
    PyObject_HEAD_INIT(NULL)
    0,                                 /* ob_size */
    "_sugarext.AddressEntry",                   /* tp_name */
    sizeof(PyGObject),          /* tp_basicsize */
    0,                                 /* tp_itemsize */
    /* methods */
    (destructor)0,        /* tp_dealloc */
    (printfunc)0,                      /* tp_print */
    (getattrfunc)0,       /* tp_getattr */
    (setattrfunc)0,       /* tp_setattr */
    (cmpfunc)0,           /* tp_compare */
    (reprfunc)0,             /* tp_repr */
    (PyNumberMethods*)0,     /* tp_as_number */
    (PySequenceMethods*)0, /* tp_as_sequence */
    (PyMappingMethods*)0,   /* tp_as_mapping */
    (hashfunc)0,             /* tp_hash */
    (ternaryfunc)0,          /* tp_call */
    (reprfunc)0,              /* tp_str */
    (getattrofunc)0,     /* tp_getattro */
    (setattrofunc)0,     /* tp_setattro */
    (PyBufferProcs*)0,  /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,                      /* tp_flags */
    NULL,                        /* Documentation string */
    (traverseproc)0,     /* tp_traverse */
    (inquiry)0,             /* tp_clear */
    (richcmpfunc)0,   /* tp_richcompare */
    offsetof(PyGObject, weakreflist),             /* tp_weaklistoffset */
    (getiterfunc)0,          /* tp_iter */
    (iternextfunc)0,     /* tp_iternext */
    (struct PyMethodDef*)NULL, /* tp_methods */
    (struct PyMemberDef*)0,              /* tp_members */
    (struct PyGetSetDef*)0,  /* tp_getset */
    NULL,                              /* tp_base */
    NULL,                              /* tp_dict */
    (descrgetfunc)0,    /* tp_descr_get */
    (descrsetfunc)0,    /* tp_descr_set */
    offsetof(PyGObject, inst_dict),                 /* tp_dictoffset */
    (initproc)0,             /* tp_init */
    (allocfunc)0,           /* tp_alloc */
    (newfunc)0,               /* tp_new */
    (freefunc)0,             /* tp_free */
    (inquiry)0              /* tp_is_gc */
};



/* ----------- functions ----------- */

static PyObject *
_wrap_sugar_mime_get_mime_type_from_file_name(PyObject *self, PyObject *args, PyObject *kwargs)
{
    static char *kwlist[] = { "filename", NULL };
    char *filename;
    const gchar *ret;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs,"s:get_mime_type_from_file_name", kwlist, &filename))
        return NULL;
    
    ret = sugar_mime_get_mime_type_from_file_name(filename);
    
    if (ret)
        return PyString_FromString(ret);
    Py_INCREF(Py_None);
    return Py_None;
}

#line 25 "_sugarext.override"
static PyObject *
_wrap_sugar_mime_get_mime_type_for_file(PyObject *self, PyObject *args, PyObject *kwargs)
{
    static char *kwlist[] = { "filename", NULL };
    char *filename;
    const gchar *ret;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs,"s:get_mime_type_for_file", kwlist, &filename))
        return NULL;
    
    ret = sugar_mime_get_mime_type_for_file(filename, NULL);
    
    if (ret)
        return PyString_FromString(ret);
    Py_INCREF(Py_None);
    return Py_None;
}
#line 123 "_sugarext.c"


static PyObject *
_wrap_sugar_x11_util_set_string_property(PyObject *self, PyObject *args, PyObject *kwargs)
{
    static char *kwlist[] = { "window", "property", "value", NULL };
    PyGObject *window;
    char *property, *value;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs,"O!ss:x11_set_string_property", kwlist, &PyGdkWindow_Type, &window, &property, &value))
        return NULL;
    
    sugar_x11_util_set_string_property(GDK_WINDOW(window->obj), property, value);
    
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject *
_wrap_sugar_x11_util_get_string_property(PyObject *self, PyObject *args, PyObject *kwargs)
{
    static char *kwlist[] = { "window", "property", NULL };
    PyGObject *window;
    char *property;
    gchar *ret;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs,"O!s:x11_get_string_property", kwlist, &PyGdkWindow_Type, &window, &property))
        return NULL;
    
    ret = sugar_x11_util_get_string_property(GDK_WINDOW(window->obj), property);
    
    if (ret) {
        PyObject *py_ret = PyString_FromString(ret);
        g_free(ret);
        return py_ret;
    }
    Py_INCREF(Py_None);
    return Py_None;
}

const PyMethodDef py_sugarext_functions[] = {
    { "get_mime_type_from_file_name", (PyCFunction)_wrap_sugar_mime_get_mime_type_from_file_name, METH_VARARGS|METH_KEYWORDS,
      NULL },
    { "get_mime_type_for_file", (PyCFunction)_wrap_sugar_mime_get_mime_type_for_file, METH_VARARGS|METH_KEYWORDS,
      NULL },
    { "x11_set_string_property", (PyCFunction)_wrap_sugar_x11_util_set_string_property, METH_VARARGS|METH_KEYWORDS,
      NULL },
    { "x11_get_string_property", (PyCFunction)_wrap_sugar_x11_util_get_string_property, METH_VARARGS|METH_KEYWORDS,
      NULL },
    { NULL, NULL, 0, NULL }
};

/* initialise stuff extension classes */
void
py_sugarext_register_classes(PyObject *d)
{
    PyObject *module;

    if ((module = PyImport_ImportModule("gtk")) != NULL) {
        _PyGtkEntry_Type = (PyTypeObject *)PyObject_GetAttrString(module, "Entry");
        if (_PyGtkEntry_Type == NULL) {
            PyErr_SetString(PyExc_ImportError,
                "cannot import name Entry from gtk");
            return ;
        }
    } else {
        PyErr_SetString(PyExc_ImportError,
            "could not import gtk");
        return ;
    }
    if ((module = PyImport_ImportModule("gtk.gdk")) != NULL) {
        _PyGdkWindow_Type = (PyTypeObject *)PyObject_GetAttrString(module, "Window");
        if (_PyGdkWindow_Type == NULL) {
            PyErr_SetString(PyExc_ImportError,
                "cannot import name Window from gtk.gdk");
            return ;
        }
    } else {
        PyErr_SetString(PyExc_ImportError,
            "could not import gtk.gdk");
        return ;
    }


#line 208 "_sugarext.c"
    pygobject_register_class(d, "SugarAddressEntry", SUGAR_TYPE_ADDRESS_ENTRY, &PySugarAddressEntry_Type, Py_BuildValue("(O)", &PyGtkEntry_Type));
}
