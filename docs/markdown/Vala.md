---
title: Vala
short-description: Compiling Vala and Genie programs
...

# Compiling Vala applications

Meson has support for compiling Vala and Genie programs. A skeleton `meson.build` file for Vala looks like this:

```meson
project('valaprog', 'vala', 'c')

glib_dep = dependency('glib-2.0')
gobject_dep = dependency('gobject-2.0')

executable('valaprog', 'prog.vala',
           dependencies : [glib_dep, gobject_dep])
```

You must always specify `glib-2.0` and `gobject-2.0` as dependencies, because all Vala applications use them.

## Using a custom VAPI

When dealing with libraries that are not providing Vala bindings, a `--vapidir` flag can be added to extend the search path for the current project.

```meson
project('vala app', 'c', 'vala')

add_project_arguments(['--vapidir', join_paths(meson.current_source_dir(), 'vapi')],
                      language: 'vala')

glib_dep = dependency('glib-2.0')
gobject_dep = dependency('gobject-2.0')
foo_dep = dependency('foo') # 'foo.vapi' will be resolved in './vapi/foo.vapi'

executable('app', 'app.vala', dependencies: [glib_dep, gobject_dep, foo_dep])
```

In this case, make sure that the VAPI name corresponds to the pkg-config file.

If no pkg-config file is provided, you must use `find_library`. Using`declare_dependency` is cleaner because it does not require passing both dependency objects to the target.

```meson
foo_lib = meson.get_compiler('c').find_library('foo') # assuming libfoo.so is installed
foo_vapi = meson.get_compiler('vala').find_library('foo', dirs: join_paths(meson.current_source_dir(), 'vapi'))
foo_dep = declare_dependency(dependencies: [foo_lib, foo_vapi])

executable('app', 'app.vala', dependencies: [glib_dep, gobject_dep, foo_dep])
```

## VAPI without pkg-config file

Some Vala bindings do not need a corresponding pkg-config file and `dependency` is unsuitable for resolving them. It's necessary to use `find_library` in this case.

```meson
posix_dep = meson.get_compiler('vala').find_library('posix')

executable('app', 'app.vala', dependencies: [glib_dep, gobject_dep, posix_dep])
```

## Custom output names

If a library target is used, Meson automatically outputs the C header and the VAPI. They can be renamed by setting the `vala_header` and `vala_vapi` arguments respectively. In this case, the second and third elements of the `install_dir` array indicate the destination with `true` to indicate default directories (i.e. `include` and `share/vala/vapi`).

```meson
foo_lib = library('foo', 'foo.vala',
                  vala_header: 'foo.h',
                  vala_vapi: 'foo-1.0.vapi',
                  dependencies: [glib_dep, gobject_dep],
                  install: true,
                  install_dir: [true, true, true])
```

## GObject Introspection

To generate GObject Introspection metadata, the `vala_gir` option has to be set with the desired name.

The fourth element in the `install_dir` array indicate where the GIR file will be installed. The `true` value tells Meson to use the default directory (i.e. `share/gir-1.0`).

```meson
foo_lib = library('foo', 'foo.vala',
                  vala_gir: 'Foo-1.0.gir',
                  dependencies: [glib_dep, gobject_dep],
                  install: true,
                  install_dir: [true, true, true, true])
```

For the typelib, use a custom target depending on the library:

```meson
g_ir_compiler = find_program('g-ir-compiler')
custom_target('foo typelib', command: [g_ir_compiler, '--output', '@OUTPUT@', '@INPUT@'],
              input: join_paths(meson.current_build_dir(), 'Foo-1.0.gir'),
              output: 'Foo-1.0.typelib',
              depends: foo_lib,
              install: true,
              install_dir: join_paths(get_option('libdir'), 'girepository-1.0'))
```
