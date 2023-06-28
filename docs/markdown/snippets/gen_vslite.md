## Added a new '--genvslite' option for use with 'meson setup ...'

To facilitate a more usual visual studio work-flow of supporting and switching between
multiple build configurations (buildtypes) within the same solution, among other
[reasons](https://github.com/mesonbuild/meson/pull/11049), use of this new option
has the effect of setting up multiple ninja back-end-configured build directories,
named with their respective buildtype suffix.  E.g. 'somebuilddir_debug',
'somebuilddir_release', etc. as well as a '_vs'-suffixed directory that contains the
generated multi-buildtype solution.  Building/cleaning/rebuilding in the solution
now launches the meson build (compile) of the corresponding buildtype-suffixed build
directory, instead of using Visual Studio's native engine.