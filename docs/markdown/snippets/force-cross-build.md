## Add `--force-cross-build` flag

This forces the build to be considered cross a build, even if it a native
build. It is intended for things which automatically use Meson, such as package
managers, distros, and Meson's own tests. See the cross compilation section of
the manual for more details.
