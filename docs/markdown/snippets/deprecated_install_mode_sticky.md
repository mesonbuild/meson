## various `install_*` functions no longer handle the sticky bit

It is not possible to portably grant the sticky bit to a file, and where
possible, it doesn't do anything. It is not expected that any users are using
this functionality.

Variously:
- on Linux, it has no meaningful effect
- on Solaris, attempting to set the permission bit is silently ignored by the OS
- on FreeBSD, attempting to set the permission bit is an error

Attempting to set this permission bit in the `install_mode:` kwarg to any
function other than [[install_emptydir]] will now result in a warning, and the
permission bit being ignored.
