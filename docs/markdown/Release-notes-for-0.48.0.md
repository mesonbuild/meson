---
title: Release 0.48
short-description: Release notes for 0.48 (preliminary)
...

# New features

This page is a placeholder for the eventual release notes.

Notable new features should come with release note updates. This is
done by creating a file snippet called `snippets/featurename.md` and
whose contents should look like this:

## More flexible `override_find_program()`.

It is now possible to pass an `executable` to
`override_find_program()` if the overridden program is not used during
configure.

This is particularly useful for fallback dependencies like protobuf
that also provide a tool like protoc.

    ## Feature name

    A short description explaining the new feature and how it should be used.

