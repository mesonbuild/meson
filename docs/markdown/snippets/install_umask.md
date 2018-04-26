## New built-in option install_umask with a default value 022

This umask is used to define the default permissions of files and directories
created in the install tree. Files will preserve their executable mode, but the
exact permissions will obey the install_umask.

The install_umask can be overridden in the meson command-line:

    $ meson --install-umask=027 builddir/

A project can also override the default in the project() call:

    project('myproject', 'c',
      default_options : ['install_umask=027'])

To disable the install_umask, set it to 'preserve', in which case permissions
are copied from the files in their origin.
