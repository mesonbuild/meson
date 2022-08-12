## A new unstable_xorg module has been added

This module provides helpers for use by the various Xorg projects. Currently, it
contains a helper for simplifying the application of the man pages that Xorg
projects create.

It also contains a port of the xtrans.m4 module's xtrans flags, which can be used as thus:
```meson
xorg = import('unstable-xorg')

xtrans = xorg.xtrans_connection()

if <have existing conf>
  conf.merge_from(xtrans)
else
  conf = xtrans
endif

configure_file(
  configuration : conf,
  output : 'config.h',
)
```
