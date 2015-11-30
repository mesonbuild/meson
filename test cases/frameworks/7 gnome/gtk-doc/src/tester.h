#ifndef GTKDOC_TESTER_H
#define GTKDOC_TESTER_H

#include <glib.h>
#include <glib-object.h>


void test (gint a);

// test for https://bugzilla.gnome.org/show_bug.cgi?id=705633
typedef struct _GtkDocTestIf GtkDocTestIf;
typedef struct _GtkDocTestIfInterface GtkDocTestIfInterface;

struct _GtkDocTestIfInterface {
    GTypeInterface parent;

};

#endif // GTKDOC_TESTER_H

