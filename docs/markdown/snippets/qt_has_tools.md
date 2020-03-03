## Added `has_tools` method to qt module

It should be used to compile optional Qt code:
```meson
qt5 = import('qt5')
if qt5.has_tools(required: get_option('qt_feature'))
  moc_files = qt5.preprocess(...)
  ...
endif
```
