## Per project subproject options rewrite

You can now define per-subproject values for all shared configuration
options. As an example you might want to enable optimizations on only
one subproject:

    meson configure -Dnumbercruncher:optimization=3

Subproject specific values can be removed with -U

    meson configure -Unumbercruncher:optimization

This is a major change in how options are handled, and the
implementation will evolve over the next few releases of Meson. If
this change causes an error in your builds, please [report an issue on
GitHub](https://github.com/mesonbuild/meson/issues/new).

We have tried to keep backwards compatibility as much as possible, but
this may lead to some build breakage.
