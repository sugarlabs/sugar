/* -- THIS FILE IS GENERATED - DO NOT EDIT *//* -*- Mode: C; c-basic-offset: 4 -*- */

#include <Python.h>



#line 4 "_sugar.override"
#include <Python.h>

#include "pygobject.h"
#include "gecko-browser.h"
#include "sugar-key-grabber.h"
#include "sugar-address-entry.h"

#line 16 "_sugar.c"


/* ---------- types from other modules ---------- */
static PyTypeObject *_PyGObject_Type;
#define PyGObject_Type (*_PyGObject_Type)
static PyTypeObject *_PyGtkEntry_Type;
#define PyGtkEntry_Type (*_PyGtkEntry_Type)
static PyTypeObject *_PyGtkMozEmbed_Type;
#define PyGtkMozEmbed_Type (*_PyGtkMozEmbed_Type)


/* ---------- forward type declarations ---------- */
PyTypeObject G_GNUC_INTERNAL PyGeckoBrowser_Type;
PyTypeObject G_GNUC_INTERNAL PySugarAddressEntry_Type;
PyTypeObject G_GNUC_INTERNAL PySugarKeyGrabber_Type;

#line 33 "_sugar.c"



/* ----------- GeckoBrowser ----------- */

static int
_wrap_gecko_browser_new(PyGObject *self, PyObject *args, PyObject *kwargs)
{
    static char* kwlist[] = { NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwargs,
                                     ":gecko.Browser.__init__",
                                     kwlist))
        return -1;

    pygobject_constructv(self, 0, NULL);
    if (!self->obj) {
        PyErr_SetString(
            PyExc_RuntimeError, 
            "could not create gecko.Browser object");
        return -1;
    }
    return 0;
}

static PyObject *
_wrap_gecko_browser_create_window(PyGObject *self)
{
    GeckoBrowser *ret;

    
    ret = gecko_browser_create_window(GECKO_BROWSER(self->obj));
    
    /* pygobject_new handles NULL checking */
    return pygobject_new((GObject *)ret);
}

static PyObject *
_wrap_GeckoBrowser__do_create_window(PyObject *cls, PyObject *args, PyObject *kwargs)
{
    gpointer klass;
    static char *kwlist[] = { "self", NULL };
    PyGObject *self;
    GeckoBrowser *ret;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs,"O!:GeckoBrowser.create_window", kwlist, &PyGeckoBrowser_Type, &self))
        return NULL;
    klass = g_type_class_ref(pyg_type_from_object(cls));
    if (GECKO_BROWSER_CLASS(klass)->create_window)
        ret = GECKO_BROWSER_CLASS(klass)->create_window(GECKO_BROWSER(self->obj));
    else {
        PyErr_SetString(PyExc_NotImplementedError, "virtual method GeckoBrowser.create_window not implemented");
        g_type_class_unref(klass);
        return NULL;
    }
    g_type_class_unref(klass);
    /* pygobject_new handles NULL checking */
    return pygobject_new((GObject *)ret);
}

static const PyMethodDef _PyGeckoBrowser_methods[] = {
    { "create_window", (PyCFunction)_wrap_gecko_browser_create_window, METH_NOARGS,
      NULL },
    { "do_create_window", (PyCFunction)_wrap_GeckoBrowser__do_create_window, METH_VARARGS|METH_KEYWORDS|METH_CLASS,
      NULL },
    { NULL, NULL, 0, NULL }
};

PyTypeObject G_GNUC_INTERNAL PyGeckoBrowser_Type = {
    PyObject_HEAD_INIT(NULL)
    0,                                 /* ob_size */
    "gecko.Browser",                   /* tp_name */
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
    (struct PyMethodDef*)_PyGeckoBrowser_methods, /* tp_methods */
    (struct PyMemberDef*)0,              /* tp_members */
    (struct PyGetSetDef*)0,  /* tp_getset */
    NULL,                              /* tp_base */
    NULL,                              /* tp_dict */
    (descrgetfunc)0,    /* tp_descr_get */
    (descrsetfunc)0,    /* tp_descr_set */
    offsetof(PyGObject, inst_dict),                 /* tp_dictoffset */
    (initproc)_wrap_gecko_browser_new,             /* tp_init */
    (allocfunc)0,           /* tp_alloc */
    (newfunc)0,               /* tp_new */
    (freefunc)0,             /* tp_free */
    (inquiry)0              /* tp_is_gc */
};

static GeckoBrowser*
_wrap_GeckoBrowser__proxy_do_create_window(GeckoBrowser *self)
{
    PyGILState_STATE __py_state;
    PyObject *py_self;
    GeckoBrowser* retval;
    PyObject *py_retval;
    PyObject *py_method;
    
    __py_state = pyg_gil_state_ensure();
    py_self = pygobject_new((GObject *) self);
    if (!py_self) {
        if (PyErr_Occurred())
            PyErr_Print();
        pyg_gil_state_release(__py_state);
        return NULL;
    }
    
    
    py_method = PyObject_GetAttrString(py_self, "do_create_window");
    if (!py_method) {
        if (PyErr_Occurred())
            PyErr_Print();
        Py_DECREF(py_self);
        pyg_gil_state_release(__py_state);
        return NULL;
    }
    py_retval = PyObject_CallObject(py_method, NULL);
    if (!py_retval) {
        if (PyErr_Occurred())
            PyErr_Print();
        Py_DECREF(py_method);
        Py_DECREF(py_self);
        pyg_gil_state_release(__py_state);
        return NULL;
    }
    if (!PyObject_TypeCheck(py_retval, &PyGObject_Type)) {
        PyErr_SetString(PyExc_TypeError, "retval should be a GObject");
        PyErr_Print();
        Py_DECREF(py_retval);
        Py_DECREF(py_method);
        Py_DECREF(py_self);
        pyg_gil_state_release(__py_state);
        return NULL;
    }
    retval = (GeckoBrowser*) pygobject_get(py_retval);
    g_object_ref((GObject *) retval);
    
    
    Py_DECREF(py_retval);
    Py_DECREF(py_method);
    Py_DECREF(py_self);
    pyg_gil_state_release(__py_state);
    
    return retval;
}

static int
__GeckoBrowser_class_init(gpointer gclass, PyTypeObject *pyclass)
{
    PyObject *o;
    GeckoBrowserClass *klass = GECKO_BROWSER_CLASS(gclass);
    PyObject *gsignals = PyDict_GetItemString(pyclass->tp_dict, "__gsignals__");

    o = PyObject_GetAttrString((PyObject *) pyclass, "do_create_window");
    if (o == NULL)
        PyErr_Clear();
    else {
        if (!PyObject_TypeCheck(o, &PyCFunction_Type)
            && !(gsignals && PyDict_GetItemString(gsignals, "create_window")))
            klass->create_window = _wrap_GeckoBrowser__proxy_do_create_window;
        Py_DECREF(o);
    }
    return 0;
}


/* ----------- SugarAddressEntry ----------- */

PyTypeObject G_GNUC_INTERNAL PySugarAddressEntry_Type = {
    PyObject_HEAD_INIT(NULL)
    0,                                 /* ob_size */
    "gecko.AddressEntry",                   /* tp_name */
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



/* ----------- SugarKeyGrabber ----------- */

static int
_wrap_sugar_key_grabber_new(PyGObject *self, PyObject *args, PyObject *kwargs)
{
    static char* kwlist[] = { NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwargs,
                                     ":gecko.KeyGrabber.__init__",
                                     kwlist))
        return -1;

    pygobject_constructv(self, 0, NULL);
    if (!self->obj) {
        PyErr_SetString(
            PyExc_RuntimeError, 
            "could not create gecko.KeyGrabber object");
        return -1;
    }
    return 0;
}

static PyObject *
_wrap_sugar_key_grabber_grab(PyGObject *self, PyObject *args, PyObject *kwargs)
{
    static char *kwlist[] = { "address", NULL };
    char *address;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs,"s:SugarKeyGrabber.grab", kwlist, &address))
        return NULL;
    
    sugar_key_grabber_grab(SUGAR_KEY_GRABBER(self->obj), address);
    
    Py_INCREF(Py_None);
    return Py_None;
}

static const PyMethodDef _PySugarKeyGrabber_methods[] = {
    { "grab", (PyCFunction)_wrap_sugar_key_grabber_grab, METH_VARARGS|METH_KEYWORDS,
      NULL },
    { NULL, NULL, 0, NULL }
};

PyTypeObject G_GNUC_INTERNAL PySugarKeyGrabber_Type = {
    PyObject_HEAD_INIT(NULL)
    0,                                 /* ob_size */
    "gecko.KeyGrabber",                   /* tp_name */
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
    (struct PyMethodDef*)_PySugarKeyGrabber_methods, /* tp_methods */
    (struct PyMemberDef*)0,              /* tp_members */
    (struct PyGetSetDef*)0,  /* tp_getset */
    NULL,                              /* tp_base */
    NULL,                              /* tp_dict */
    (descrgetfunc)0,    /* tp_descr_get */
    (descrsetfunc)0,    /* tp_descr_set */
    offsetof(PyGObject, inst_dict),                 /* tp_dictoffset */
    (initproc)_wrap_sugar_key_grabber_new,             /* tp_init */
    (allocfunc)0,           /* tp_alloc */
    (newfunc)0,               /* tp_new */
    (freefunc)0,             /* tp_free */
    (inquiry)0              /* tp_is_gc */
};



/* ----------- functions ----------- */

static PyObject *
_wrap_gecko_browser_startup(PyObject *self)
{
    
    gecko_browser_startup();
    
    Py_INCREF(Py_None);
    return Py_None;
}

const PyMethodDef py_sugar_functions[] = {
    { "startup_browser", (PyCFunction)_wrap_gecko_browser_startup, METH_NOARGS,
      NULL },
    { NULL, NULL, 0, NULL }
};

/* initialise stuff extension classes */
void
py_sugar_register_classes(PyObject *d)
{
    PyObject *module;

    if ((module = PyImport_ImportModule("gobject")) != NULL) {
        _PyGObject_Type = (PyTypeObject *)PyObject_GetAttrString(module, "GObject");
        if (_PyGObject_Type == NULL) {
            PyErr_SetString(PyExc_ImportError,
                "cannot import name GObject from gobject");
            return ;
        }
    } else {
        PyErr_SetString(PyExc_ImportError,
            "could not import gobject");
        return ;
    }
    if ((module = PyImport_ImportModule("gtkmozembed")) != NULL) {
        _PyGtkMozEmbed_Type = (PyTypeObject *)PyObject_GetAttrString(module, "MozEmbed");
        if (_PyGtkMozEmbed_Type == NULL) {
            PyErr_SetString(PyExc_ImportError,
                "cannot import name MozEmbed from gtkmozembed");
            return ;
        }
    } else {
        PyErr_SetString(PyExc_ImportError,
            "could not import gtkmozembed");
        return ;
    }
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


#line 425 "_sugar.c"
    pygobject_register_class(d, "GeckoBrowser", GECKO_TYPE_BROWSER, &PyGeckoBrowser_Type, Py_BuildValue("(O)", &PyGtkMozEmbed_Type));
    pyg_set_object_has_new_constructor(GECKO_TYPE_BROWSER);
    pyg_register_class_init(GECKO_TYPE_BROWSER, __GeckoBrowser_class_init);
    pygobject_register_class(d, "SugarAddressEntry", SUGAR_TYPE_ADDRESS_ENTRY, &PySugarAddressEntry_Type, Py_BuildValue("(O)", &PyGtkEntry_Type));
    pygobject_register_class(d, "SugarKeyGrabber", SUGAR_TYPE_KEY_GRABBER, &PySugarKeyGrabber_Type, Py_BuildValue("(O)", &PyGObject_Type));
    pyg_set_object_has_new_constructor(SUGAR_TYPE_KEY_GRABBER);
}
