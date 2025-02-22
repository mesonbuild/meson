#ifndef MESON_PYTHON_SAMPLE_H
#define MESON_PYTHON_SAMPLE_H

#include <glib-object.h>

G_BEGIN_DECLS

#define MESON_TYPE_PYTHON_SAMPLE (meson_python_sample_get_type())

G_DECLARE_FINAL_TYPE (MesonPythonSample, meson_python_sample, MESON, SAMPLE, GObject)

MesonPythonSample *meson_python_sample_new           (void);
void               meson_python_sample_print_message (MesonPythonSample *self);

G_END_DECLS

#endif /* MESON_PYTHON_SAMPLE_H */
