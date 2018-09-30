---
title: Release 0.50
short-description: Release notes for 0.49 (preliminary)
...

# New features

This page is a placeholder for the eventual release notes.

Notable new features should come with release note updates. This is
done by creating a file snippet called `snippets/featurename.md` and
whose contents should look like this:

    ## Feature name

    A short description explaining the new feature and how it should be used.

## custom_target: install no longer overrides build_by_default

Earlier, if `build_by_default` was set to false and `install` was set to true in
a `custom_target`, `install` would override it and the `custom_target` would
always be built by default.
Now if `build_by_default` is explicitly set to false it will no longer be
overridden. If `build_by_default` is not set, its default will still be
determined by the value of `install` for greater backward compatibility.
