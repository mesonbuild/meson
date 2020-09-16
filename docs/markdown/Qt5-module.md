# Qt5 module

The Qt5 module provides tools to automatically deal with the various
tools and steps required for Qt. The module has several methods.

## preprocess

This method takes the following keyword arguments:
 - `moc_headers`, `moc_sources`, `ui_files`, `qresources`, which define the files that require preprocessing with `moc`, `uic` and `rcc`
 - `include_directories`, the directories to add to header search path for `moc` (optional)
 - `moc_extra_arguments`, any additional arguments to `moc` (optional). Available since v0.44.0.
 - `uic_extra_arguments`, any additional arguments to `uic` (optional). Available since v0.49.0.
 - `rcc_extra_arguments`, any additional arguments to `rcc` (optional). Available since v0.49.0.
 - `dependencies`, dependency objects needed by moc. Available since v0.48.0.

It returns an opaque object that should be passed to a main build target.

## compile_translations (since v0.44.0)

This method generates the necessary targets to build translation files with lrelease, it takes the following keyword arguments:
 - `ts_files`, the list of input translation files produced by Qt's lupdate tool.
 - `install` when true, this target is installed during the install step (optional).
 - `install_dir` directory to install to (optional).
 - `build_by_default` when set to true, to have this target be built by default, that is, when invoking `meson compile`; the default value is false (optional).
 - `qresource` rcc source file to extract ts_files from; cannot be used with ts_files kwarg. Available since v0.56.0.
 - `rcc_extra_arguments`, any additional arguments to `rcc` (optional), when used with `qresource. Available since v0.56.0.

Returns either: a list of custom targets for the compiled translations, or, if
using a `qresource` file, a single custom target containing the processed
source file, which should be passed to a main build target.

## has_tools

This method returns `true` if all tools used by this module are found, `false`
otherwise.

It should be used to compile optional Qt code:
```meson
qt5 = import('qt5')
if qt5.has_tools(required: get_option('qt_feature'))
  moc_files = qt5.preprocess(...)
  ...
endif
```

This method takes the following keyword arguments:
- `required`: by default, `required` is set to `false`. If `required` is set to
  `true` or an enabled [`feature`](Build-options.md#features) and some tools are
  missing Meson will abort.
- `method`: method used to find the Qt dependency (`auto` by default).

*Since: 0.54.0*

## is_static
This method returnes `true` if the Qt install is statically built.

*Since 0.56.0*

## static_plugins_dep
When linking against a statically built Qt installation, plugins also needs static linking. The `static_plugins_dep` return a dependecy object that holds the nessecary
linker flags for static linking, and generates files that includes the plugins using Qt's `Q_IMPORT_PLUGIN`. Normal plugins (those found in the `plugins` folder) must
needs to be specified manually, while QML plugins are automatically detected from QML and JavaScript files.

The method takes the following keyword arguments:
- `qresources`, rcc source file used for scanning for QML plugins
- `qmlfiles`, sources files used for scanning for QML plugins
- `plugins`, list of plugins to import

```meson
qt5 = import('qt5')
if qt5.is_static()
  plugins_dep = qt5.static_plugins_dep(plugins: ['qsqlite', 'qjpeg'], qresources: 'resources.qrc')
endif
```
*Since 0.56.0*


## Dependencies

See [Qt dependencies](Dependencies.md#qt4-qt5)

The 'modules' argument is used to include Qt modules in the project.
See the Qt documentation for the [list of modules](http://doc.qt.io/qt-5/qtmodules.html).

The 'private_headers' argument allows usage of Qt's modules private headers.
(since v0.47.0)

## Example
A simple example would look like this:

```meson
qt5 = import('qt5')
qt5_dep = dependency('qt5', modules: ['Core', 'Gui'])
inc = include_directories('includes')
moc_files = qt5.preprocess(moc_headers : 'myclass.h',
                           moc_extra_arguments: ['-DMAKES_MY_MOC_HEADER_COMPILE'],
                           include_directories: inc,
                           dependencies: qt5_dep)
translations = qt5.compile_translations(ts_files : 'myTranslation_fr.ts', build_by_default : true)
executable('myprog', 'main.cpp', 'myclass.cpp', moc_files,
           include_directories: inc,
           dependencies : qt5_dep)
```

Sometimes, translations are embedded inside the binary using qresource files.
In this case the ts files do not need to be explicitly listed. For example:

```meson
qt5 = import('qt5')
qt5_dep = dependency('qt5', modules: ['Core', 'Gui'])
lang_cpp = qt5.compile_translations(qresource: 'lang.qrc')
executable('myprog', 'main.cpp', lang_cpp,
           dependencies: qt5_dep)
```
