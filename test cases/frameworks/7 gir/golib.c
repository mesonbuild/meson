#include "golib.h"
#include <stdio.h>

G_DEFINE_TYPE (MesonSample, meson_sample, G_TYPE_OBJECT)

#define MESON_SAMPLE_GET_PRIVATE(o) \
        (G_TYPE_INSTANCE_GET_PRIVATE ((o), MESON_SAMPLE_TYPE, MesonSamplePrivate))

struct _MesonSamplePrivate {
    gchar *msg;
};

enum {
    PROP_0,
    PROP_MSG,
    N_PROPERTIES
};

static GParamSpec *obj_properties[N_PROPERTIES] = { NULL, };

static void meson_sample_init (MesonSample *object)
{
    MesonSamplePrivate *priv = MESON_SAMPLE_GET_PRIVATE (object);
    priv->msg = NULL;
}
static void meson_sample_finalize (GObject *object)
{
    MesonSamplePrivate *priv = MESON_SAMPLE_GET_PRIVATE (object);
    g_free (priv->msg);
    G_OBJECT_CLASS (meson_sample_parent_class)->finalize (object);
}

static void meson_sample_set_property (GObject *object,
        guint property_id,
        const GValue *value,
        GParamSpec *pspec) {
    MesonSamplePrivate *priv = MESON_SAMPLE_GET_PRIVATE (object);
    switch (property_id) {
    case PROP_MSG:
        g_free (priv->msg);
        priv->msg = g_value_dup_string (value);
        break;
    default:
        G_OBJECT_WARN_INVALID_PROPERTY_ID (object, property_id, pspec);
        break;
    }
}

static void meson_sample_get_property (GObject *object,
        guint property_id,
        GValue *value,
        GParamSpec *pspec) {
    MesonSamplePrivate *priv = MESON_SAMPLE_GET_PRIVATE (object);
    switch (property_id) {
    case PROP_MSG:
        g_value_set_string (value, priv->msg);
        break;
    default:
        G_OBJECT_WARN_INVALID_PROPERTY_ID (object, property_id, pspec);
        break;
    }
}

static void meson_sample_class_init (MesonSampleClass *klass) {
    GObjectClass *object_class = G_OBJECT_CLASS (klass);
    object_class->set_property = meson_sample_set_property;
    object_class->get_property = meson_sample_get_property;
    object_class->finalize = meson_sample_finalize;

    obj_properties[PROP_MSG] =
            g_param_spec_string ("msg",
                    "Msg",
                    "The message to print.",
                    "propertytext",
                    G_PARAM_READWRITE |
                    G_PARAM_CONSTRUCT);
    g_object_class_install_properties (object_class,
            N_PROPERTIES,
            obj_properties);
    g_type_class_add_private (object_class, sizeof (MesonSamplePrivate));
}

MesonSample* meson_sample_new () {
    MesonSample *sample;
    sample = g_object_new(MESON_SAMPLE_TYPE, NULL);
    return sample;
}

void meson_sample_func (MesonSample *sample) {
    MesonSamplePrivate *priv;
    g_return_if_fail (sample != NULL);
    priv = MESON_SAMPLE_GET_PRIVATE(sample);
    printf("GObject introspection is working, %s!\n", priv->msg);
}
