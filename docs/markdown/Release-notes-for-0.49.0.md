---
title: Release 0.49
short-description: Release notes for 0.49 (preliminary)
...

# New features

This page is a placeholder for the eventual release notes.

Notable new features should come with release note updates. This is
done by creating a file snippet called `snippets/featurename.md` and
whose contents should look like this:

    ## Feature name

    A short description explaining the new feature and how it should be used.

## Libgcrypt dependency now supports libgcrypt-config

Earlier, `dependency('libgcrypt')` could only detect the library with pkg-config
files. Now, if pkg-config files are not found, Meson will look for
`libgcrypt-config` and if it's found, will use that to find the library.
