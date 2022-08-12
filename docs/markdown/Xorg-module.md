---
short-description: Xorg development helper module
authors:
    - name: Dylan Baker
      email: dylan@pnwbakers.com
      years: [2021, 2022]
...

# Unstable Xorg module

*(new in 0.64.0)*

**Note** Unstable modules make no backwards compatible API guarantees.

The Xorg module provides helper functions for common upstream Xorg build tasks.

## Functions

### format_man

```
  format_man(template: string | File, section: string, apploaddir: string = ''): CustomTarget
```

This function creates a CustomTarget to format man pages, and is a replacement
for the `xorg_manpage_sections` macros from the xorg-macros.m4. The template is
the input file, with `__replacement__` style inputs, the section is the man
section (as a named string, see [table below](#man-sections)), and the apploaddir
keyword arguments is the value to use for the `__apploaddir__` value in the
template. If that keyword is not provided then an empty string is used.

This function understands the difference between the old Sunos scheme and the
traditional unix scheme used by most modern Unix-like OSes (including Linux, the
BSDs and modern Solaris)

For cases where the autodetection doesn't work, such as in cross compilation cases,
the `-Dxorg.man-sections=...` option can be used to override the detection.

```meson
xorg = import('unstable-xorg')
xorg.format_man('man.page', 'lib')
```

#### Man sections

| string name | Old Sunos number | traditional number |
| ----------- | ---------------- | ------------------ |
| app         | 1                | 1                  |
| driver      | 7                | 4                  |
| admin       | 1m               | 8                  |
| lib         | 3                | 3                  |
| misc        | 5                | 7                  |
| file        | 4                | 5                  |


### xtrans_connection

```
  xtrans_connection(): ConfiguratinoData
```

This function provides an equivalent to the xtrans.m4 macro
`XTRANS_CONNECTION_FLAGS`. It takes no options, and returns a ConfigurationData
object, such as would be returned by `configuration_data()`. It uses three new,
module specific options, the `xorg.xtrans-tcp-transport`,
`xorg.xtrans-unix-transport` and `xorg.xtrans-local-transport`

The first option is a boolean option, which defaults to `true`, the latter two
are feature options, and default to `auto`. It can be used as follows:

```meson
xorg = import('unstable-xorg')

conf = xorg.xtrans_connection()

configure_file(
  configuration : conf,
  output : config.h,
)
```

If you already have a `configuration_data` object, you can merge them together:

```meson
xorg = import('unstable-xorg')

conf = configuration_data()
conf.merge_from(xorg.xtrans_connection())

configure_file(
  configuration : conf,
  output : config.h,
)
```
