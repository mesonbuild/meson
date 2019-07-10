## alias_target

``` meson
runtarget alias_target(target_name, dep1, ...)
```

This function creates a new top-level target. Like all top-level targets, this
integrates with the selected backend. For instance, with Ninja you can
run it as `ninja target_name`. This is a dummy target that does not execute any
command, but ensures that all dependencies are built. Dependencies can be any
build target (e.g. return value of executable(), custom_target(), etc)

