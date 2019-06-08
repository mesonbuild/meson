## CMake prefix path overrides

When using pkg-config as a dependency resolver we can pass
`-Dpkg_config_path=$somepath` to extend or overwrite where pkg-config will
search for dependencies. Now cmake can do the same, as long as the dependency
uses a ${Name}Config.cmake file (not a Find{$Name}.cmake file), by passing
`-Dcmake_prefix_path=list,of,paths`. It is important that point this at the
prefix that the dependency is installed into, not the cmake path.

If you have installed something to `/tmp/dep`, which has a layout like:
```
/tmp/dep/lib/cmake
/tmp/dep/bin
```

then invoke meson as `meson builddir/ -Dcmake_prefix_path=/tmp/dep`
