#include<stdio.h>
#include<string.h>
#include<gio/gio.h>
#include"generated-resources.h"

#define EXPECTED "This is a generated resource.\n"

int main(int argc, char **argv) {
    const gchar *contents;
    GResource *res = generated_resources_get_resource();
    GError *err = NULL;
    GBytes *data = g_resources_lookup_data("/com/example/myprog/res3.txt",
            G_RESOURCE_LOOKUP_FLAGS_NONE, &err);

    if(data == NULL) {
        fprintf(stderr, "Data lookup failed: %s\n", err->message);
        return 1;
    }
    contents = g_bytes_get_data(data, NULL);
    if(strcmp(contents, EXPECTED) != 0) {
        fprintf(stderr, "Resource contents are wrong:\n'%s'\n", contents);
        fprintf(stderr, "Should be:\n'%s'", EXPECTED);
        return 1;
    }
    fprintf(stdout, "All ok.\n");
    g_bytes_unref(data);
    g_resource_unref(res);
    return 0;
}
