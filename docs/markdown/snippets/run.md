## Build and run the project

[`Meson run`](Commands.md#run) compiles and runs a target inside Meson's
[`devenv`](Commands.md#devenv).

In the case the project installs more than one executable, `--bin <target>`
argument can be used to specify which one to run. See [`compile`](#compile)
command for `target` syntax.

The remainder of the command line are arguments passed to the target executable:
```
meson run -C builddir --bin gst-launch-1.0 videotestsrc ! glimagesink
```
