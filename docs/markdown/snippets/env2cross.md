## Experimental command to convert environments to cross files

Meson has a new command `env2mfile` that can be used to convert
"environment variable based" cross and native compilation environments
to Meson machine files. This is especially convenient for e.g. distro
packagers so they can easily generate unambiguous configuration files
for packge building.

As an example here's how you would generate a cross file that takes
its settings from the `CC`, `CXX`, `CFLAGS` etc environment variables.

    meson env2mfile --cross --system=baremetal --cpu=armv7 --cpu-family=arm -o armcross.txt

The command also has support for generating Debian build files using
system introspection:

    meson env2mfile --cross --debarch armhf -o debarmhf_cross.txt

Note how you don't need to specify any system details, the command
gets them transparently via `dpkg-architecture`.

Creating a native file is done in the same way:

    meson env2mfile --native -o current_system.txt

This system will detect if the `_FOR_BUILD` environment variables are
enabled and then uses them as needed.

With this you should be able to convert any envvar-based cross build
setup to cross and native files and then use those. Thit means, among
other things, that you can then run your compilations from any shell,
not just the special one that has all the environment variables set.

As this functionality is still a bit in flux, the specific behaviour
and command line arguments to use are subject to change. Because of
this the main documentation has not yet been updated.

Please try this for your use cases and report to us if it is working.
Patches to make the autodetection work on other distros and platforms
are also welcome.
