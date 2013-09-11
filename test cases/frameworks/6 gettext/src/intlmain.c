#include<libintl.h>
#include<locale.h>
#include<stdio.h>

#define _(String) gettext (String)
#define gettext_noop(String) String
#define N_(String) gettext_noop (String)

#define PACKAGE "intltest"
// WRONG, but enough for this test.
#define LOCALEDIR "/usr/share/locale"

int main(int argc, char **argv) {
    setlocale(LC_ALL, "");
    bindtextdomain(PACKAGE, LOCALEDIR);
    textdomain(PACKAGE);
    printf("%s\n", _("International greeting."));
    return 0;
}
