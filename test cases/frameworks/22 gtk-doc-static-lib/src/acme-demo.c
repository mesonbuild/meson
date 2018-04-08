
#include "acme-demo.h"

G_DEFINE_TYPE(AcmeDemo, acme_demo, G_TYPE_OBJECT);

AcmeDemo *acme_demo_new(void)
{
    return g_object_new(ACME_TYPE_DEMO, NULL);
}

static void acme_demo_class_init(AcmeDemoClass *klass)
{

}

static void acme_demo_init(AcmeDemo *demo)
{
}

