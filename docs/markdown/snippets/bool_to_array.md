## New method `to_array` for bool

This function provides a compact idiom to select optional sources or dependencies,
as in the following example:

```meson
is_windows = host_machine.system() == 'windows'
sources += is_windows.to_array('util-win32.c')
sources += (!is_windows).to_array('util-posix.c')
executable('prog', sources: sources)
```
