---
title: Release 0.42
short-description: Release notes for 0.42 (preliminary)
...

**Preliminary, 0.42.0 has not been released yet.**

# New features

## Distribution tarballs from Mercurial repositories

Creating distribution tarballs can now be made out of projects based on
Mercurial. As before, this remains possible only with the Ninja backend.

## Keyword argument verification

Meson will now check the keyword arguments used when calling any function
and print a warning if any of the keyword arguments is not known. In the
future this will become a hard error.

