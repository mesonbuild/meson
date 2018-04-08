#pragma once

#include <glib-object.h>


#define ACME_TYPE_DEMO            (acme_demo_get_type ())
#define ACME_DEMO(obj)            (G_TYPE_CHECK_INSTANCE_CAST ((obj), ACME_TYPE_DEMO, AcmeDemo))
#define ACME_DEMO_CLASS(klass)    (G_TYPE_CHECK_CLASS_CAST ((klass), ACME_TYPE_DEMO, AcmeDemoClass))
#define ACME_IS_DEMO(obj)         (G_TYPE_CHECK_INSTANCE_TYPE ((obj), ACME_TYPE_DEMO))
#define ACME_IS_DEMO_CLASS(klass) (G_TYPE_CHECK_CLASS_TYPE ((klass), ACME_TYPE_DEMO))
#define ACME_DEMO_GET_CLASS(obj)  (G_TYPE_INSTANCE_GET_CLASS ((obj), ACME_TYPE_DEMO, AcmeDemoClass))


typedef struct _AcmeDemo AcmeDemo;
typedef struct _AcmeDemoPrivate AcmeDemoPrivate;
typedef struct _AcmeDemoClass AcmeDemoClass;

struct _AcmeDemo
{
    GObject parent;
};

struct _AcmeDemoClass
{
    GObjectClass parent_class;
};


GType acme_demo_get_type(void) G_GNUC_CONST;

AcmeDemo *acme_demo_new(void);
