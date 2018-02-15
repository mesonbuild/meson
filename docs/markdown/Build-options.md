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
option('integer_opt', type : 'integer', min : 0, max : 5, value : 3) # Since 0.45.0
option('free_array_opt', type : 'array', value : ['one', 'two'])
option('array_opt', type : 'array', choices : ['one', 'two', 'three'], value : ['one', 'two'])
```

All types allow a `description` value to be set describing the option,
if no option is set then the name of the option will be used instead.

### Strings

The string type is a free form string. If the default value is not set
then an empty string will be used as the default.

### Booleans

Booleans may have values of either `true` or `false`. If no default
value is supplied then `true` will be used as the default.

### Combos

A combo allows any one of the values in the `choices` parameter to be
selected.  If no default value is set then the first value will be the
default.

## Integers

An integer option contains a single integer with optional upper and
lower values that are specified with the `min` and `max` keyword
arguments.

This type is available since Meson version 0.45.0.

### Arrays

Arrays represent an array of strings. By default the array can contain
arbitrary strings. To limit the possible values that can used set the
`choices` parameter. Meson will then only allow the value array to
contain strings that are in the given list. The array may be
empty. The `value` parameter specifies the default value of the option
and if it is unset then the values of `choices` will be used as the
default.

This type is available since version 0.44.0


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
scripts. They have to be set externally with the `meson configure`
command line tool. Running `meson configure` without arguments in a
build dir shows you all options you can set.

To change their values use the `-D`
option:

```console
$ meson configure -Doption=newvalue
```

Setting the value of arrays is a bit special. If you only pass a
single string, then it is considered to have all values separated by
commas. Thus invoking the following command:

```console
$ meson configure -Darray_opt=foo,bar
```

would set the value to an array of two elements, `foo` and `bar`.

If you need to have commas in your string values, then you need to
pass the value with proper shell quoting like this:

```console
$ meson configure "-Doption=['a,b', 'c,d']"
```

The inner values must always be single quotes and the outer ones
double quotes.

To change values in subprojects prepend the name of the subproject and
a colon:

```console
$ meson configure -Dsubproject:option=newvalue
```

**NOTE:** If you cannot call `meson configure` you likely have a old
  version of Meson. In that case you can call `mesonconf` instead, but
  that is deprecated in newer versions

## Yielding to superproject option

Suppose you have a master project and a subproject. In some cases it
might be useful to have an option that has the same value in both of
them. This can be achieved with the `yield` keyword. Suppose you have
an option definition like this:

```meson
option('some_option', type : 'string', value : 'value', yield : true)
```

If you build this project on its own, this option behaves like
usual. However if you build this project as a subproject of another
project which also has an option called `some_option`, then calling
`get_option` returns the value of the superproject. If the value of
`yield` is `false`, `get_option` returns the value of the subproject's
option.
