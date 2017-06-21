#include <glib.h>

static void test_source (void)
{
    const char *in_file = g_test_get_filename (G_TEST_DIST, "file.in", NULL);
    g_assert_true (g_file_test (in_file, G_FILE_TEST_EXISTS));
}

static void test_build (void)
{
    const char *out_file = g_test_get_filename (G_TEST_BUILT, "file.out", NULL);
    g_assert_true (g_file_test (out_file, G_FILE_TEST_EXISTS));
}

int main(int argc, char **argv)
{
    g_test_init (&argc, &argv, NULL);

    g_test_add_func ("/test_srcdir", test_source);
    g_test_add_func ("/test_builddir", test_build);

    return g_test_run ();
}
