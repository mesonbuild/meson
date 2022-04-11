## It is now possible to customize the setup arguments to ninja dist

A new function has been added: [[meson.add_dist_args]]. This allows specifying
arguments which will be used in the generated `ninja dist` target to customize
how the distcheck stage will configure the build. By default a distcheck simply
uses the same configuration as the main build.
