#include <Python.h>
#include <string.h>

static PyObject *hello(PyObject *self, PyObject *args) {
  return PyLong_FromLong(42);
}

static PyMethodDef methods[] = {{"hello", hello, METH_NOARGS, "Hello World"},
                                {NULL, NULL, 0, NULL}};

static struct PyModuleDef mod = {PyModuleDef_HEAD_INIT, "test", NULL, -1,
                                 methods};

PyMODINIT_FUNC PyInit_mod2(void) { return PyModule_Create(&mod); }
