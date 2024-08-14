## Per project subproject options rewrite

A common requirement when building large projects with many
subprojects is to build some (or all) subprojects with project options
that are different from the "main project". This has been sort of
possible in a limited way but is now possible in a general way. These
additions can be added, changed and removed at runtime using the
command line or, in other words, without editing existing
`meson.build` files.

Since this release you can specify _augments_, which are basically
per-project option settings. These can be specified for every top
level (i.e. not project) options. Suppose you have a project that has
a single subproject called `numbercruncher` that does heavy
computation. During development you want to build that subproject with
optimizations enabled but your main project without
optimizations. This can be done by specifying an augment to the given
subproject:

    meson configure -Anumbercruncher:optimization=3

Another case might be that you want to build with errors as warnings,
but some subproject does not support it. It would be set up like this:

    meson configure -Dwerror=true -Anaughty:werror=false

You can also specify an augment on the opt level project. A more
general version of enabling optimizations on all subprojects but not
the top project would be done like this:

    meson configure -Doptimization=2 -A:optimization=0

Note the colon after `A`.

Augments can be removed with -U

    meson configure -Usubproject:optionnname

This is a major change in how options are handled. Current
per-subproject options are converted to augments on the fly. It is
expected that the logic might be changed in the next few releases as
logical gaffes are discovered.

We have tried to keep backwards compatibility as much as possible, but
this may lead to some build breakage.
