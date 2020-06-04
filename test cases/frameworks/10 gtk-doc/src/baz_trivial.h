/*
  In the namespace 'Baz', 'Trivial' is a trivial Gobject-drived type
*/

/* inclusion guard */
#ifndef __BAZ_TRIVIAL_H__
#define __BAZ_TRIVIAL_H__

#include <glib-object.h>

G_BEGIN_DECLS

/*
 * Type declaration.
 */
#define BAZ_TYPE_TRIVIAL baz_trivial_get_type ()
G_DECLARE_FINAL_TYPE (BazTrivial, baz_trivial, BAZ, TRIVIAL, GObject)

/*
 * Method definitions.
 */

/**
 * baz_trivial_method:
 *
 * This is a trivial method operating on a trivial object.
 *
 * It would be a mistake to call this expecting something useful to happen.
 *
 **/
void baz_trivial_method(BazTrivial *self, GError **error);

G_END_DECLS

#endif /* __BAZ_TRIVIAL_H__ */
