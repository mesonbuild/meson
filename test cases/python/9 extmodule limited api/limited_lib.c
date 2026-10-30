#include <Python.h>

#ifndef Py_LIMITED_API
#error Py_LIMITED_API must be defined.
#elif Py_LIMITED_API != 0x03070000
#error Wrong value for Py_LIMITED_API
#endif

PyObject *
hello(PyObject * Py_UNUSED(self), PyObject * Py_UNUSED(args)) {
    return PyUnicode_FromString("hello world");
}
