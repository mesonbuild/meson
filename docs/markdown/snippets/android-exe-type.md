## New argument `android_exe_type` for executables

Android application executables actually need to be linked
as a shared object, which is loaded from a pre-warmed JVM.
Meson projects can now specify a new argument `android_exe_type`
and set it to `application`, in order produce such a shared library
only on Android targets.

This makes it possible to use the same `meson.build` file
for both Android and non-Android systems.
