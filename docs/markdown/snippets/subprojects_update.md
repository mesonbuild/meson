## `meson subprojects` command

A new `--types` argument has been added to all subcommands to run the command only
on wraps with the specified types. For example this command will only print `Hello`
for each git subproject: `meson subprojects foreach --types git echo "Hello"`.
Multiple types can be set as comma separated list e.g. `--types git,file`.

Subprojects with no wrap file are now taken into account as well. This happens
for example for subprojects configured as git submodule, or downloaded manually
by the user and placed into the `subprojects/` directory.

The `checkout` subcommand now always stash any pending changes before switching
branch. Note that `update` subcommand was already stashing changes before updating
the branch.

If the command fails on any subproject the execution continues with other
subprojects, but at the end an error code is now returned.

The `update` subcommand has been reworked:
- In the case the URL of `origin` is different as the `url` set in wrap file,
  the subproject will not be updated unless `--reset` is specified (see below).
- In the case a subproject directory exists and is not a git repository but has
  a `[wrap-git]`, meson used to run git commands that would wrongly apply to the
  main project. It now skip the subproject unless `--reset` is specified (see below).
- The `--rebase` behaviour is now the default for consistency: it was
  already rebasing when current branch and revision are the same, it is
  less confusing to rebase when they are different too.
- Add `--reset` mode that checkout the new branch and hard reset that
  branch to remote commit. This new mode guarantees that every
  subproject are exactly at the wrap's revision. In addition the URL of `origin`
  is updated in case it changed in the wrap file. If the subproject directory is
  not a git repository but has a `[wrap-git]` the directory is deleted and the
  new repository is cloned.
- Local changes are always stashed first to avoid any data loss. In the
  worst case scenario the user can always check reflog and stash list to
  rollback.
