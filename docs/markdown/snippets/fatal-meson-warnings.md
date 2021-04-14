## `--fatal-meson-warnings` added to 'configure' task

There was previously no way to enable fatal Meson warnings for the
'configure' task. Hence it was easy to miss that an unknown option,
e.g. caused by a typo, was encountered, since only a warning was
emitted while Meson would exit without an error code. If
`--fatal-meson-warnings` is now given, the 'configure' task will exit
with an error code if an unknown Meson option was encountered.
