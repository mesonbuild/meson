#include <Python.h>

#ifndef Py_LIMITED_API
#error Py_LIMITED_API must be defined.
#elif Py_LIMITED_API != 0x03070000
#error Wrong value for Py_LIMITED_API
#endif

static PyObject *
hello(PyObject * Py_UNUSED(self), PyObject * Py_UNUSED(args)) {
    return PyUnicode_FromString("hello world");
}

static struct PyMethodDef methods[] = {
    { "hello", hello, METH_NOARGS, NULL },
    { NULL, NULL, 0, NULL },
};

static struct PyModuleDef limited_module = {
   PyModuleDef_HEAD_INIT,
   "limited",
   NULL,
   -1,
   methods
};

PyMODINIT_FUNC PyInit_limited(void) {
    return PyModule_Create(&limited_module);
}
