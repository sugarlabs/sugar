/* -- THIS FILE IS GENERATED - DO NOT EDIT *//* -*- Mode: C; c-basic-offset: 4 -*- */

#include <Python.h>



#line 4 "extensions.override"
#include <Python.h>

#include "pygobject.h"
#include "sugar-key-grabber.h"
#include "sugar-address-entry.h"
#include "sugar-audio-manager.h"

#line 16 "extensions.c"


/* ---------- types from other modules ---------- */
static PyTypeObject *_PyGObject_Type;
#define PyGObject_Type (*_PyGObject_Type)
static PyTypeObject *_PyGtkEntry_Type;
#define PyGtkEntry_Type (*_PyGtkEntry_Type)


/* ---------- forward type declarations ---------- */
PyTypeObject G_GNUC_INTERNAL PySugarKeyGrabber_Type;
PyTypeObject G_GNUC_INTERNAL PySugarAudioManager_Type;

#line 30 "extensions.c"



/* ----------- SugarKeyGrabber ----------- */

static PyObject *
_wrap_sugar_key_grabber_grab(PyGObject *self, PyObject *args, PyObject *kwargs)
{
    static char *kwlist[] = { "key", NULL };
    char *key;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs,"s:SugarKeyGrabber.grab", kwlist, &key))
        return NULL;
    
    sugar_key_grabber_grab(SUGAR_KEY_GRABBER(self->obj), key);
    
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject *
_wrap_sugar_key_grabber_get_key(PyGObject *self, PyObject *args, PyObject *kwargs)
{
    static char *kwlist[] = { "keycode", "state", NULL };
    PyObject *py_keycode = NULL, *py_state = NULL;
    gchar *ret;
    guint keycode = 0, state = 0;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs,"OO:SugarKeyGrabber.get_key", kwlist, &py_keycode, &py_state))
        return NULL;
    if (py_keycode) {
        if (PyLong_Check(py_keycode))
            keycode = PyLong_AsUnsignedLong(py_keycode);
        else if (PyInt_Check(py_keycode))
            keycode = PyInt_AsLong(py_keycode);
        else
            PyErr_SetString(PyExc_TypeError, "Parameter 'keycode' must be an int or a long");
        if (PyErr_Occurred())
            return NULL;
    }
    if (py_state) {
        if (PyLong_Check(py_state))
            state = PyLong_AsUnsignedLong(py_state);
        else if (PyInt_Check(py_state))
            state = PyInt_AsLong(py_state);
        else
            PyErr_SetString(PyExc_TypeError, "Parameter 'state' must be an int or a long");
        if (PyErr_Occurred())
            return NULL;
    }
    
    ret = sugar_key_grabber_get_key(SUGAR_KEY_GRABBER(self->obj), keycode, state);
    
    if (ret) {
        PyObject *py_ret = PyString_FromString(ret);
        g_free(ret);
        return py_ret;
    }
    Py_INCREF(Py_None);
    return Py_None;
}

static const PyMethodDef _PySugarKeyGrabber_methods[] = {
    { "grab", (PyCFunction)_wrap_sugar_key_grabber_grab, METH_VARARGS|METH_KEYWORDS,
      NULL },
    { "get_key", (PyCFunction)_wrap_sugar_key_grabber_get_key, METH_VARARGS|METH_KEYWORDS,
      NULL },
    { NULL, NULL, 0, NULL }
};

PyTypeObject G_GNUC_INTERNAL PySugarKeyGrabber_Type = {
    PyObject_HEAD_INIT(NULL)
    0,                                 /* ob_size */
    "extensions.KeyGrabber",                   /* tp_name */
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
    (initproc)0,             /* tp_init */
    (allocfunc)0,           /* tp_alloc */
    (newfunc)0,               /* tp_new */
    (freefunc)0,             /* tp_free */
    (inquiry)0              /* tp_is_gc */
};



/* ----------- SugarAudioManager ----------- */

static PyObject *
_wrap_sugar_audio_manager_set_volume(PyGObject *self, PyObject *args, PyObject *kwargs)
{
    static char *kwlist[] = { "level", NULL };
    int level;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs,"i:SugarAudioManager.set_volume", kwlist, &level))
        return NULL;
    
    sugar_audio_manager_set_volume(SUGAR_AUDIO_MANAGER(self->obj), level);
    
    Py_INCREF(Py_None);
    return Py_None;
}

static const PyMethodDef _PySugarAudioManager_methods[] = {
    { "set_volume", (PyCFunction)_wrap_sugar_audio_manager_set_volume, METH_VARARGS|METH_KEYWORDS,
      NULL },
    { NULL, NULL, 0, NULL }
};

PyTypeObject G_GNUC_INTERNAL PySugarAudioManager_Type = {
    PyObject_HEAD_INIT(NULL)
    0,                                 /* ob_size */
    "extensions.AudioManager",                   /* tp_name */
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
    (struct PyMethodDef*)_PySugarAudioManager_methods, /* tp_methods */
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

const PyMethodDef pyextensions_functions[] = {
    { NULL, NULL, 0, NULL }
};

/* initialise stuff extension classes */
void
pyextensions_register_classes(PyObject *d)
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


#line 256 "extensions.c"
    pygobject_register_class(d, "SugarKeyGrabber", SUGAR_TYPE_KEY_GRABBER, &PySugarKeyGrabber_Type, Py_BuildValue("(O)", &PyGObject_Type));
    pyg_set_object_has_new_constructor(SUGAR_TYPE_KEY_GRABBER);
    pygobject_register_class(d, "SugarAudioManager", SUGAR_TYPE_AUDIO_MANAGER, &PySugarAudioManager_Type, Py_BuildValue("(O)", &PyGObject_Type));
    pyg_set_object_has_new_constructor(SUGAR_TYPE_AUDIO_MANAGER);
}
