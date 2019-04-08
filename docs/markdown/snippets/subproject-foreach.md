## Add new `meson subprojects foreach` command

`meson subprojects` has learned a new `foreach` command which accepts a command
with arguments and executes it in each subproject directory.

For example this can be useful to check the status of subprojects (e.g. with
`git status` or `git diff`) before performing other actions on them.
