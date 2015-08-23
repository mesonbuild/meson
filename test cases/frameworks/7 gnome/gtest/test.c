#include <glib.h>
 
gint
compute (gint x, gint y)
{
  return x * y;
}

void
test_meson (void)
{
  g_assert_cmpint(4, ==, compute(2, 2));
}
 
gint
main (gint   argc,
      gchar *argv[])
{
  g_test_init (&argc, &argv, NULL);

  g_test_add_func ("/meson/unit", test_meson);

  return g_test_run();
}
