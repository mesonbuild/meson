#ifndef PRIVATE_FUNCTION_H
#define PRIVATE_FUNCTION_H

#if !defined (MESON_TEST)
#error "MESON_TEST not defined."
#endif

#include <glib-object.h>

G_BEGIN_DECLS

#define PRIVATE_TYPE_FUNCTION (private_function_get_type())
G_DECLARE_FINAL_TYPE (PrivateFunction, private_function, PRIVATE, FUNCTION, GObject)

PrivateFunction *private_function_new      (void);
int              private_function_return_0 (PrivateFunction *self);

G_END_DECLS

#endif /* PRIVATE_FUNCTION_H */
