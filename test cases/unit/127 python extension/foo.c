#define PY_SSIZE_T_CLEAN
#include <Python.h>


static PyObject *
bar_impl(PyObject *self, PyObject *args)
{
    return Py_None;
}


static PyMethodDef foo_methods[] = {
    {"bar", bar_impl, METH_NOARGS, NULL},
    {NULL, NULL, 0, NULL} /* sentinel */
};


static struct PyModuleDef foo_module = {
    PyModuleDef_HEAD_INIT,
    "foo", /* m_name */
    NULL, /* m_doc */
    -1, /* m_size */
    foo_methods, /* m_methods */
};


PyMODINIT_FUNC
PyInit_foo(void)
{
    return PyModule_Create(&foo_module);
}
