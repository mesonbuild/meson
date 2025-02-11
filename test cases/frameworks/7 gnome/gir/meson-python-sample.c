#include "meson-python-sample.h"

#include <Python.h>

struct _MesonPythonSample
{
  GObject parent_instance;
};

G_DEFINE_TYPE (MesonPythonSample, meson_python_sample, G_TYPE_OBJECT)

/**
 * meson_python_sample_new:
 *
 * Allocates a new #MesonPythonSample.
 *
 * Returns: (transfer full): a #MesonPythonSample.
 */
MesonPythonSample *
meson_python_sample_new (void)
{
  return g_object_new (MESON_TYPE_PYTHON_SAMPLE, NULL);
}

static void
meson_python_sample_class_init (MesonPythonSampleClass *klass)
{
  if (!Py_IsInitialized ()) {
    Py_Initialize ();
    Py_Finalize ();
  }
}

static void
meson_python_sample_init (MesonPythonSample *self)
{
}

/**
 * meson_python_sample_print_message:
 * @self: a #MesonSample2.
 *
 * Prints Hello.
 *
 * Returns: Nothing.
 */
void
meson_python_sample_print_message (MesonPythonSample *self)
{
  g_print ("Message: Hello\n");
}
