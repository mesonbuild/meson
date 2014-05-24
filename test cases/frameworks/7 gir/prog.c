#include<glib.h>
#include<glib-object.h>
#include"golib.h"

int main (int argc, char *argv[])
{
    MesonSample *i;

    i = meson_sample_new();
    meson_sample_func(i);
    g_object_unref(G_OBJECT(i));

    return 0;
}

