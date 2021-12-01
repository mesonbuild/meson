## Support for CMake <3.14 is now deprecated for CMake subprojects

In CMake 3.14, the File API was introduced and the old CMake server API was
deprecated (and removed in CMake 3.20). Thus support for this API will also
be removed from Meson in future releases.

This deprecation only affects CMake subprojects.
