## Add `optimization` `plain` option

The `optimization` built-in option now accepts `plain` value,
which will not set any optimization flags. This is now the default
value of the flag for `buildtype=plain`, which is useful for distros,
that set the optimization and hardening flags by other means.

If you are using the value of `get_option('optimization')` in your
Meson scripts, make sure you are not making assumptions about it,
such as that the value can be passed to a compiler in `-O` flag.
