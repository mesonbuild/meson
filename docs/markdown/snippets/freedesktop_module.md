## A new freedesktop module for common freedesktop operations

This module include useful functionality for projects that use freedesktop standards, such as .desktop files.

```meson
exe = executable(..., gui_app : true, install : true)

fdo = import('freedesktop')
exe_desktop = fdo.desktop_file(
    exe,
    name : 'UnicornAwesomeApp',
    generic_name : 'Email',
    ...
)
```
