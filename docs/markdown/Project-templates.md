---
short-description: Project templates
...

# Project templates

To make it easier for new developers to start working, Meson ships a
tool to generate the basic setup of different kinds of projects. This
functionality can be accessed with the `meson init` command. A typical
project setup would go like this:

```console
$ mkdir project_name
$ cd project_name
$ meson init --language=c --name=myproject --version=0.1
```

This would create the build definitions for a helloworld type
project. The result can be compiled as usual. For example compiling it
with Ninja could be done like this:

```
$ meson builddir
$ ninja -C builddir
```

The generator has many different projects and settings. They can all
be listed by invoking the command `meson test --help`.

This feature is available since Meson version 0.45.0.
