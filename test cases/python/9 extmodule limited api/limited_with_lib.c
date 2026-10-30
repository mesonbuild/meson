#include <Python.h>

#ifndef Py_LIMITED_API
#error Py_LIMITED_API must be defined.
#elif Py_LIMITED_API != 0x03070000
#error Wrong value for Py_LIMITED_API
#endif

PyObject *
hello(PyObject * Py_UNUSED(self), PyObject * Py_UNUSED(args));

static struct PyMethodDef methods[] = {
    { "hello", hello, METH_NOARGS, NULL },
    { NULL, NULL, 0, NULL },
};

static struct PyModuleDef limited_with_lib_module = {
   PyModuleDef_HEAD_INIT,
   "limited_with_lib",
   NULL,
   -1,
   methods
};

PyMODINIT_FUNC PyInit_limited_with_lib(void) {
    return PyModule_Create(&limited_with_lib_module);
}
