#include "baz_trivial.h"

/* instance structure */
struct _BazTrivial
{
  GObject parent_instance;
};

static void
baz_trivial_init(BazTrivial *self)
{
}

static void
baz_trivial_class_init(BazTrivialClass *self)
{
}

G_DEFINE_TYPE (BazTrivial, baz_trivial, G_TYPE_OBJECT)

void
baz_trivial_method(BazTrivial *self, GError **error)
{
}
