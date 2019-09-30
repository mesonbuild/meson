## Improved support for static libraries

Static libraries had numerous shortcomings in the past, especially when using
uninstalled static libraries. This release brings many internal changes in the
way they are handled, including:

- `link_whole:` of static libraries. In the example below, lib2 used to miss
  symbols from lib1 and was unusable.
```meson
lib1 = static_library(sources)
lib2 = static_library(other_sources, link_whole : lib1, install : true)
```
- `link_with:` of a static library with an uninstalled static library. In the
example below, lib2 now implicitly promote `link_with:` to `link_whole:` because
the installed lib2 would oterhwise be unusable.
```meson
lib1 = static_library(sources, install : false)
lib2 = static_library(sources, link_with : lib1, install : true)
```
- pkg-config generator do not include uninstalled static libraries. In the example
  below, the generated `.pc` file used to be unusable because it contained
  `Libs.private: -llib1` and `lib1.a` is not installed. `lib1` is now ommitted
  from the `.pc` file because the `link_with:` has been promoted to
  `link_whole:` (see above) and thus lib1 is not needed to use lib2.
```meson
lib1 = static_library(sources, install : false)
lib2 = both_libraries(sources, link_with : lib1, install : true)
pkg.generate(lib2)
```

Many projects have been using `extract_all_objects()` to work around those issues,
and hopefully those hacks could now be removed. Since this is a pretty large
change, please double check if your static libraries behave correctly, and
report any regression.
