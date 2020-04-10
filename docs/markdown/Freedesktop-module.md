# Freedesktop Module

This module provides helper functions for freedesktop standards used primarily on *nix systems.

*New in 0.55.0*

## File generators

### desktop_file()

```meson
  custom_target desktop_file(exe, ...)
```

Helper for generating a [.desktop file](https://specifications.freedesktop.org/desktop-entry-spec/latest/index.html)

Creates a custom_target that will be installed if the executable used to
generate it is also installed. Takes one positional argument which is an
executable or a disabler. If a disabler is passed or the executable is not
going to be installed then nothing is returned.

The `Exec` field is automatically populated with the installed path to the executable.

The `Terminal` field is set based on the value of the Executable's `gui_app` field.

This function has the following keyword arguments:

- `name` The name of the program. This is the value of the `Name` field in
  the .desktop file. If this field is not set then the name of the executable
  is used.

- `comment` The value of the `Comment` field in the .desktop file. If this
  value is not provided then the field is unset.

- `generic_name` is the `GenericName` in the .desktop file. If this value is
  not provided then the field is unset.

- `icon` is the `Icon` value in the .desktop file. Meson does not validate
  this value in anyway. If not provided the field is unset.

- `categories` a meson list of categories for this program. These values will
  be joined into a single semicolon delimited string in the .desktop file.
  Meson does not validate this value in any way. If not provided the field is
  unset.

- `install_name` The name of the .desktop file without the file extension. If
  this is unset the name of the value of `name` or the name of the executable
  will be used, in that order.

- `mimetype` A meson list of mimetypes that this program handles. These
  values will be joined into a single semicolon delimited string in the
  .desktop file. Meson does not validate these values in any way. If not
  provided the field is unset.

- `dbus` A boolean that populates the `DBusActivatable` field in the .desktop
file. Defaults to false

- `no_display` A boolean for the `NoDisplay` field.

- `only_show_in` A list of strings to populate the `OnlyShowIn` field.

- `not_show_in` A list of strings to populate the `NotShowIn` field.

- `startup_notify` A Boolean for to populate the `StartupNotify` field.

- `startup_wm_class` A Boolean for to populate the `StartupWMClass` field.

- `implements` A list of strings that will be `;` joined to populate the
  `Implements` field.

- `keywords` A list of strings that will be `;` joined to populate the
  `Keywords` field.

- `extra_args` A dict of string to string|list of string|boolean's for
  extended attributes. The keys must start with `X-`. Lists will be converted
  in `;` delimited strings. If a value needs to be formatted differently the
  caller must format it themselves and pass the value as a string. Meson
  validates only that all keys start with `X-`, it is up to the caller to
  ensure that these keys are correctly formatted.

- `test_target` A boolean. If this is set to true then a test target to
  validate the .desktop file is also generated. If this is true then the
  program `desktop-file-validate` is required

- `actions` A list of dictionaries for additional actions for the .desktop
  file. If this value is not provided then no additional actions are set.

The actions dictionaries have the following signature:

- `exec` Additional arguments to pass to the Executable. The path to the
  executable is provided, these are treated as extra arguments. Required.

- `name` the name of the action. Required.

- `icon` Icon for the action, uses the same logic as the main `icon`
  argument. Optional.

```meson
fdo = import('freedesktop')

exe = executable(..., gui_app : true, install : true)
fdo.desktop_file(
  exe,
  generic_name : 'IDE',
  actions : [
    {
      name : 'Import',
      exec : ['--import', '%f'],
    }
  ]
)
```
