#include <stdlib.h>
#include <stddef.h>
#include <stdio.h>
#include <assert.h>

#ifndef _WIN32
#include <dlfcn.h>
#else
#include <windows.h>
#endif

typedef struct {
  const char *library_name;
  const char *func_name;
  char        expected_result;
} test_t;

static void
load (test_t *test)
{
#ifndef _WIN32
  void *h = dlopen (test->library_name, RTLD_NOW | RTLD_LOCAL);
  if (h == NULL) {
    fprintf (stderr, "dlopen (%s) failed: %s\n",
             test->library_name, dlerror ());
    exit (EXIT_FAILURE);
  }

  typedef char (*func_t)(void);
  func_t func = (func_t) dlsym (h, test->func_name);
  assert (func != NULL);

  assert (func () == test->expected_result);
  dlclose (h);
#else /* _WIN32 */
  HMODULE h = LoadLibraryA (test->library_name);
  if (h == NULL) {
    fprintf (stderr, "LoadLibrary (%s) failed with error code %u\n",
             test->library_name, (unsigned int) GetLastError ());
    exit (EXIT_FAILURE);
  }

  typedef char (*func_t)(void);
  func_t func = (func_t) GetProcAddress (h, test->func_name);
  assert (func != NULL);

  assert (func () == test->expected_result);
  FreeLibrary (h);
#endif
}

#define STRINGIFY_HELPER(x) #x
#define STRINGIFY(x) STRINGIFY_HELPER(x)

int
main (void)
{
  test_t tests[] = {
    {STRINGIFY (LIBA), "func_a", 'a'},
    {STRINGIFY (LIBB), "func_b", 'b'},
  };

  for (size_t i = 0; i < sizeof (tests) / sizeof (tests[0]); i++)
    load (&tests[i]);

  return 0;
}
