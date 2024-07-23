## Dependencies from CMake subprojects now use only PUBLIC link flags

Any [[@dep]] obtained from a CMake subproject (or `.wrap` with `method = cmake`)
now only includes link flags marked in CMake as `PUBLIC` or `INTERFACE`.
Flags marked as `PRIVATE` are now only applied when building the subproject
library and not when using it as a dependency. This better matches how CMake
handles link flags and fixes link errors when using some CMake projects as
subprojects.
