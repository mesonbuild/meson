# Qt5 module

The Qt5 module provides tools to automatically deal with the various
tools and steps required for Qt. The module has one method.

## preprocess

This method takes the following keyword arguments:
 - `moc_headers`, `moc_sources`, `ui_files`, `qresources`, which define the files that require preprocessing with `moc`, `uic` and `rcc`
 - `include_directories`, the directories to add to header search path for `moc` (optional)
 - `moc_extra_arguments`, any additional arguments to `moc` (optional). Available since v0.44.0.

It returns an opaque object that should be passed to a main build target.

A simple example would look like this:

```meson
qt5 = import('qt5')
qt5_dep = dependency('qt5', modules: ['Core', 'Gui'])
inc = include_directories('includes')
moc_files = qt5.preprocess(moc_headers : 'myclass.h', include_directories: inc)
executable('myprog', 'main.cpp', 'myclass.cpp', moc_files,
           include_directories: inc,
           dependencies : qt5_dep)
```


The 'modules' argument is used to include Qt modules in the project.
See the Qt documentation for the [list of
modules](http://doc.qt.io/qt-5/qtmodules.html).
