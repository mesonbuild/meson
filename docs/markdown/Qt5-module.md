# Qt5 module

The Qt5 module provides tools to automatically deal with the various tools and steps required for Qt. The module has one method.

## preprocess

This method takes four keyword arguments, `moc_headers`, `moc_sources`, `ui_files` and `qresources` which define the files that require preprocessing with `moc`, `uic` and `rcc`. It returns an opaque object that should be passed to a main build target. A simple example would look like this:

```meson
qt5 = import('qt5')
qt5_dep = dependency('qt5', modules: ['Core', 'Gui'])
moc_files = qt5.preprocess(moc_headers : 'myclass.h')
executable('myprog', 'main.cpp', 'myclass.cpp', moc_files,
           dependencies : qt5_dep)
```


The 'modules' argument is used to include Qt modules in the project.  You can determine the list of valid module names by looking at `$QTDIR/include`.  The 'Core' module has a directory in `$QTDIR/include/QtCore` and a library named `Qt5Core.lib`.  'Network' has `$QTDIR/include/QtNetwork` and Qt5Network.lib.  And so on.
