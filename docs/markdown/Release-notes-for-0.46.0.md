---
title: Release 0.46
short-description: Release notes for 0.46 (preliminary)
...

# New features

This page is a placeholder for the eventual release notes.

Notable new features should come with release note updates. This is
done by creating a file snippet called `snippets/featurename.md` and
whose contents should look like this:

    ## Feature name

    A short description explaining the new feature and how it should be used.

## Allow early return from a script

Added the function `subdir_done()`. Its invocation exits the current script at
the point of invocation. All previously invoked build targets and commands are
build/executed. All following ones are ignored. If the current script was
invoked via `subdir()` the parent script continues normally.
