#include <girepository.h>

#include "meson-sample.h"

gint
main (gint   argc,
      gchar *argv[])
{
  g_autoptr(GError) error = NULL;

  g_autoptr(GOptionContext) ctx = g_option_context_new (NULL);
  g_option_context_add_group (ctx, g_irepository_get_option_group ());

  if (!g_option_context_parse (ctx, &argc, &argv, &error)) {
    g_print ("sample: %s\n", error->message);
    return 1;
  }

  g_autoptr(MesonSample) i = meson_sample_new ("Hello, meson/c!");
  meson_sample_print_message (i);

  return 0;
}
