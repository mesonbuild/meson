#include<gio/gio.h>

#include"meson-resources.h"

int main(void) {
  GResource *resource;
  GError *error = NULL;

  resource = meson_get_resource ();
  if (!g_resource_get_info (resource, "/org/freedesktop/Meson/example.txt",
                            G_RESOURCE_LOOKUP_FLAGS_NONE,
                            NULL, NULL, &error)) {
    g_print ("sample: %s\n", error->message);
    g_resource_unref (resource);
    return 1;
  }

  g_resource_unref (resource);
  return 0;
}
