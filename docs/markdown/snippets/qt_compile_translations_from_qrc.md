## Qt5 compile_translations now supports qresource preprocessing

When using qtmod.preprocess() in combination with qtmod.compile_translations()
to embed translations using rcc, it is no longer required to do this:

```meson
ts_files = ['list', 'of', 'files']
qtmod.compile_translations(ts_files)
# lang.qrc also contains the duplicated list of files
lang_cpp = qtmod.preprocess(qresources: 'lang.qrc')
```

Instead, use:
```meson
lang_cpp = qtmod.compile_translations(qresource: 'lang.qrc')
```

which will automatically detect and generate the needed compile_translations
targets.
