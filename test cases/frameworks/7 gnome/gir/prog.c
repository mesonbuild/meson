#include <girepository.h>

#include "meson-sample.h"

gint
main (gint   argc,
      gchar *argv[])
{
  GError * error = NULL;

  GOptionContext * ctx = g_option_context_new (NULL);
  g_option_context_add_group (ctx, g_irepository_get_option_group ());

  if (!g_option_context_parse (ctx, &argc, &argv, &error)) {
    g_print ("sample: %s\n", error->message);
    g_option_context_free (ctx);
    if (error) {
      g_error_free (error);
    }

    return 1;
  }

  MesonSample * i = meson_sample_new ("Hello, meson/c!");
  meson_sample_print_message (i);

  g_object_unref (i);
  g_option_context_free (ctx);

  return 0;
}
