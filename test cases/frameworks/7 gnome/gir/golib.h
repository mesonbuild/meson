#ifndef GOLIB_H
#define GOLIB_H

#if !defined (MESON_TEST)
#error "MESON_TEST not defined."
#endif

#include <glib.h>
#include <glib-object.h>

#define MESON_SAMPLE_TYPE \
        (meson_sample_get_type())
#define MESON_SAMPLE(o) \
        (G_TYPE_CHECK_INSTANCE_CAST ((o), MESON_SAMPLE_TYPE, MesonSample))
#define MESON_SAMPLE_CLASS(c) \
        (G_TYPE_CHECK_CLASS_CAST ((c), MESON_SAMPLE_TYPE, MesonSampleClass))
#define MESON_IS_SAMPLE(o) \
        (G_TYPE_CHECK_INSTANCE_TYPE ((o), MESON_SAMPLE_TYPE))
#define MESON_IS_SAMPLE_CLASS(c) \
        (G_TYPE_CHECK_CLASS_TYPE ((c), MESON_SAMPLE_TYPE))
#define MESON_SAMPLE_GET_CLASS(o) \
        (G_TYPE_INSTANCE_GET_CLASS ((o), MESON_SAMPLE_TYPE, MesonSampleClass))

typedef struct _MesonSample MesonSample;
typedef struct _MesonSamplePrivate MesonSamplePrivate;
typedef struct _MesonSampleClass MesonSampleClass;

struct _MesonSample {
    GObject parent;
};

struct _MesonSampleClass {
    GObjectClass parent;
};

GType meson_sample_get_type () G_GNUC_CONST;
MesonSample* meson_sample_new (void);

void meson_sample_func (MesonSample *sample);

#endif
