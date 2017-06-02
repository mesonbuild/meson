---
short-description: Using meson projects as subprojects within other meson projects
...

# Subprojects

Some platforms do not provide a native packaging system. In these cases it is common to bundle all third party libraries in your source tree. This is usually frowned upon because it makes it hard to add these kinds of projects into e.g. those Linux distributions that forbid bundled libraries.

Meson tries to solve this problem by making it extremely easy to provide both at the same time. The way this is done is that Meson allows you to take any other Meson project and make it a part of your build without (in the best case) any changes to its Meson setup. It becomes a transparent part of the project. The basic idiom goes something like this.

```meson
dep = dependency('foo', required : false)
if dep.found()
  # set up project using external dependency
else
  subproject('foo')
  # set up rest of project as if foo was provided by this project
endif
```

All Meson features of the subproject, such as project options keep working and can be set in the master project. There are a few limitations, the most important being that global compiler arguments must be set in the main project before calling subproject. Subprojects must not set global arguments because there is no way to do that reliably over multiple subprojects. To check whether you are running as a subproject, use the `is_subproject` function.

As an example, suppose we have a simple project that provides a shared library.

```meson
project('simple', 'c')
i = include_directories('include')
l = shared_library('simple', 'simple.c', include_directories : i, install : true)
```

Then we could use that from a master project. First we generate a subdirectory called `subprojects` in the root of the master directory. Then we create a subdirectory called `simple` and put the subproject in that directory. Now the subproject can be used like this.

```meson
project('master', 'c')
dep = dependency('simple', required : false)
if dep.found()
  i = []
  l = []
else
  sp = subproject('simple') # This is a name of a subdirectory in subprojects.
  i = sp.get_variable('i')
  l = sp.get_variable('l')
endif
exe = executable('prog', 'prog.c', include_directories : i, link_with : l,
                 deps : dep, install : true)
```

With this setup the system dependency is used when it is available, otherwise we fall back on the bundled version.

It should be noted that this only works for subprojects that are built with Meson. It can not be used with any other build system. The reason is the simple fact that there is no possible way to do this reliably with mixed build systems.

Subprojects can use other subprojects, but all subprojects must reside in the top level `subprojects` directory. Recursive use of subprojects is not allowed, though, so you can't have subproject `a` that uses subproject `b` and have `b` also use `a`.

## Subprojects and dependencies

A common use case is to use subprojects to provide dependencies on platforms that do not provide them out of the box. This is especially common on Windows. Meson makes this easy while at the same time using system dependencies if are available. The way to do this is to set up a subproject that builds the dependency and has an internal dependency declared like this:

```meson
proj_dep = declare_dependency(...)
```

Then you can use the subproject in the master project like this:

```meson
sp_dep = dependency('subproj_pkgconfig_name', fallback : ['subproj_name', 'proj_dep']
```

This uses the system dependency when available and the self built version if not. If you want to always use the subproject, that is also possible, just use `subproject` and `get_variable` as discussed above to get the dependency object.

# Obtaining subprojects

Meson ships with a dependency system to automatically obtain dependency subprojects. It is documented in the [Wrap dependency system manual](Wrap-dependency-system-manual.md).
