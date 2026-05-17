## Non-default members of Cargo workspaces can now be built

The new keyword argument `extra_members` to the `workspace()` method
allows configuring non-default members of a Cargo workspace.  Previously,
non-default members were never used for dependency resolution and
could not be built.
