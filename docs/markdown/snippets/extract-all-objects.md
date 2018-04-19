## Recursively extract objects

`recursive` keyword argument has been added to `extract_all_objects`. When set
to `true` it will also return objects passed to the `objects` argument of this
target. By default only objects built for this target are returned to maintain
backward compatibility with previous versions. The default will eventually be
changed to `true` in a future version.

```meson
lib1 = static_library('a', 'source.c', objects : 'prebuilt.o')
lib2 = static_library('b', objects : lib1.extract_all_objects(recursive : true))
```
