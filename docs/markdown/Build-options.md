# Build options

Most non-trivial builds require user-settable options. As an example a program may have two different data backends that are selectable at build time. Meson provides for this by having a option definition file. Its name is `meson_options.txt` and it is placed at the root of your source tree.

Here is a simple option file.

```meson
option('someoption', type : 'string', value : 'optval', description : 'An option')
option('other_one', type : 'boolean', value : false)
option('combo_opt', type : 'combo', choices : ['one', 'two', 'three'], value : 'three')
```

This demonstrates the three basic option types and their usage. String option is just a free form string and a boolean option is, unsurprisingly, true or false. The combo option can have any value from the strings listed in argument `choices`. If `value` is not set, it defaults to empty string for strings, `true` for booleans or the first element in a combo. You can specify `description`, which is a free form piece of text describing the option. It defaults to option name.

These options are accessed in Meson code with the `get_option` function.

```meson
optval = get_option('opt_name')
```

This function also allows you to query the value of Meson's built-in project options. For example, to get the installation prefix you would issue the following command:

```meson
prefix = get_option('prefix')
```

It should be noted that you can not set option values in your Meson scripts. They have to be set externally with the `mesonconf` command line tool. Running `mesonconf` without arguments in a build dir shows you all options you can set. To change their values use the `-D` option:

```console
$ mesonconf -Doption=newvalue
```
