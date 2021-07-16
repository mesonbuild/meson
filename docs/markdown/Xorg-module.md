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
