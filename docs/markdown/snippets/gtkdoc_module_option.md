## New option gnome.gtkdoc to disable building HTML docs

There is now a builtin feature option `-Dgnome.gtkdoc=enabled` that controls
whether to build gtkdoc-based documentation, and newly allows disabling its
creation or installation.

When defined as auto, gtkdoc will build documentation only when all the tools
it needs are found.

Existing project options used to control whether to run the gtkdoc() function
will still work, but should be removed in favor of the builtin solution.
