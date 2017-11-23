# Qt5 module

The Qt5 module provides tools to automatically deal with the various
tools and steps required for Qt. The module has two methods.

## preprocess

This method takes the following keyword arguments:
 - `moc_headers`, `moc_sources`, `ui_files`, `qresources`, which define the files that require preprocessing with `moc`, `uic` and `rcc`
 - `include_directories`, the directories to add to header search path for `moc` (optional)
 - `moc_extra_arguments`, any additional arguments to `moc` (optional). Available since v0.44.0.

It returns an opaque object that should be passed to a main build target.

## compile_translations (since v0.44.0)

This method generates the necessary targets to build translation files with lrelease, it takes the following keyword arguments:
 - `ts_files`, the list of input translation files produced by Qt's lupdate tool.
 - `install` when true, this target is installed during the install step (optional).
 - `install_dir` directory to install to (optional).
 - `build_by_default` when set to true, to have this target be built by default, that is, when invoking plain ninja; the default value is false (optional).

A simple example would look like this:

```meson
qt5 = import('qt5')
qt5_dep = dependency('qt5', modules: ['Core', 'Gui'])
inc = include_directories('includes')
moc_files = qt5.preprocess(moc_headers : 'myclass.h',
                           moc_extra_arguments: ['-DMAKES_MY_MOC_HEADER_COMPILE'],
                           include_directories: inc)
translations = qt5.compile_translations(ts_files : 'myTranslation_fr.ts', build_by_default : true)
executable('myprog', 'main.cpp', 'myclass.cpp', moc_files,
           include_directories: inc,
           dependencies : qt5_dep)
```


The 'modules' argument is used to include Qt modules in the project.
See the Qt documentation for the [list of modules](http://doc.qt.io/qt-5/qtmodules.html).
