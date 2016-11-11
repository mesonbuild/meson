#include "private-function.h"

struct _PrivateFunction
{
  GObject parent_instance;
};

G_DEFINE_TYPE (PrivateFunction, private_function, G_TYPE_OBJECT)

/**
 * private_function_new:
 *
 * Allocates a new #PrivateFunction.
 *
 * Returns: (transfer full): a #PrivateFunction.
 */
PrivateFunction *
private_function_new (void)
{
  return g_object_new (PRIVATE_TYPE_FUNCTION, NULL);
}

static void
private_function_class_init (PrivateFunctionClass *klass)
{
}

static void
private_function_init (PrivateFunction *self)
{
}

/**
 * private_function_return_0:
 * @self: a #PrivateFunction.
 *
 * Prints the message.
 *
 * Returns: 0.
 */
int
private_function_return_0 (PrivateFunction *self)
{
  g_assert (PRIVATE_IS_FUNCTION (self));

  return 0;
}
