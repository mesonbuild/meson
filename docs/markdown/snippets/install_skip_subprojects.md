## Skip subprojects installation

It is now possible to skip installation of some or all subprojects. This is
useful when subprojects are internal dependencies static linked into the main
project.

By default all subprojects are still installed.
- `meson install -C builddir --skip-subprojects` installs only the main project.
- `meson install -C builddir --skip-subprojects foo,bar` installs the main project
  and all subprojects except for subprojects `foo` and `bar` if they are used.
