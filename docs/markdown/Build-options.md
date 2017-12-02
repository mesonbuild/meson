---
short-description: Build options to configure project properties
...

# Build options

Most non-trivial builds require user-settable options. As an example a
program may have two different data backends that are selectable at
build time. Meson provides for this by having a option definition
file. Its name is `meson_options.txt` and it is placed at the root of
your source tree.

Here is a simple option file.

```meson
option('someoption', type : 'string', value : 'optval', description : 'An option')
option('other_one', type : 'boolean', value : false)
option('combo_opt', type : 'combo', choices : ['one', 'two', 'three'], value : 'three')
option('array_opt', type : 'array', choices : ['one', 'two', 'three'], value : ['one', 'two'])
```

All types allow a `description` value to be set describing the option, if no
option is set then the name of the option will be used instead.

### Strings

The string type is a free form string. If the default value is not set then an
empty string will be used as the default.

### Booleans

Booleans may have values of either `true` or `false`. If not default value is
supplied then `true` will be used as the default.

### Combos

A combo allows any one of the values in the `choices` parameter to be selected.
If no default value is set then the first value will be the default.

### Arrays

Arrays allow one or more of the values in the `choices` parameter to be selected.
If the `value` parameter is unset then the values of `choices` will be used as
the default.

This type is new in version 0.44.0


## Using build options

```meson
optval = get_option('opt_name')
```

This function also allows you to query the value of Meson's built-in
project options. For example, to get the installation prefix you would
issue the following command:

```meson
prefix = get_option('prefix')
```

It should be noted that you can not set option values in your Meson
scripts. They have to be set externally with the `meson configure` command
line tool. Running `meson configure` without arguments in a build dir shows
you all options you can set.

To change their values use the `-D`
option:

```console
$ meson configure -Doption=newvalue
```


**NOTE:** If you cannot call `meson configure` you likely have a old version of Meson. In that case you can call `mesonconf` instead, but that is deprecated in newer versions
