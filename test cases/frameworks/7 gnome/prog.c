#include"golib.h"

#include<girepository.h>

int main(int argc, char *argv[]) {
    GOptionContext *ctx;
    GError *error = NULL;
    MesonSample *i;

    ctx = g_option_context_new(NULL);
    g_option_context_add_group(ctx, g_irepository_get_option_group ());

    if (!g_option_context_parse(ctx, &argc, &argv, &error)) {
        g_print("sample: %s\n", error->message);
        return 1;
    }

    i = meson_sample_new();
    meson_sample_func(i);
    g_object_unref(G_OBJECT(i));

    return 0;
}

