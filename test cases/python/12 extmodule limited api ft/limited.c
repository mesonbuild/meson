#include <Python.h>

#ifndef Py_LIMITED_API
#error Py_LIMITED_API must be defined.
#elif Py_LIMITED_API != 0x030f0000
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

PyABIInfo_VAR(abi_info);

static PySlot limited_module_slots[] = {
    PySlot_STATIC_DATA(Py_mod_name, "limited"),
    PySlot_STATIC_DATA(Py_mod_methods, methods),
    PySlot_STATIC_DATA(Py_mod_gil, Py_MOD_GIL_NOT_USED),
    PySlot_STATIC_DATA(Py_mod_abi, &abi_info),
    PySlot_END,
};

PyMODEXPORT_FUNC PyModExport_limited(void) {
    return limited_module_slots;
}

PyMODINIT_FUNC PyInit_limited(void) {
    PyErr_SetString(PyExc_NotImplementedError, "legacy init not supported");
    return NULL;
}
