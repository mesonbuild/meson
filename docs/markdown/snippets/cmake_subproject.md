## Autodetect CMake subproject

Any subproject that has `CMakeLists.txt` file and not `meson.build` will
transparently be configured using CMake. For example:
```meson
  sub_pro = subproject('libsimple_cmake')
  dep = dependency('simple', fallback : ['libsimple_cmake', 'simplelib_dep'])
```
