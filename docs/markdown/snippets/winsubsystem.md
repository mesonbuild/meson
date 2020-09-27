## Add support for all Windows subsystem types

It is now possible to build things like Windows kernel drivers with
the new `win_subsystem` keyword argument. This replaces the old
`gui_app` keyword argument, which is now deprecated. You should update
your project to use the new style like this:

```meson
# Old way
executable(..., gui_app: 'true')
# New way
executable(..., win_subsystem: 'windows')
```

The argument supports versioning [as described on MSDN
documentation](https://docs.microsoft.com/en-us/cpp/build/reference/subsystem-specify-subsystem).
Thus to build a Windows kernel driver with a specific version you'd
write something like this:

```meson
executable(..., win_subsystem: 'native,6.02')
```
