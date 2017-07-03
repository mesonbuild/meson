---
title: Release 0.43
short-description: Release notes for 0.43 (preliminary)
...

# New features

This page is a placeholder for the eventual release notes.

Notable new features should come with release note updates. This is
done by creating a file snippet called `snippets/featurename.md` and
whose contents should look like this:

    # Feature name

    A short description explaining the new feature and how it should be used.

# `install_data()` defaults to `{datadir}/{projectname}`

If `install_data()` is not given an `install_dir` keyword argument, the
target directory defaults to `{datadir}/{projectname}` (e.g.
`/usr/share/myproj`).
