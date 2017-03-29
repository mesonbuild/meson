# Wrap best practices and tips

There are several things you need to take into consideration when writing a Meson build definition for a project. This is especially true when the project will be used as a subproject. This page lists a few things to consider when writing your definitions.

## Do not put config.h in external search path

Many projects use a `config.h` header file that they use for configuring their project internally. These files are never installed to the system header files so there are no inclusion collisions. This is not the case with subprojects, your project tree may have an arbitrary number of configuration files, so we need to ensure they don't clash.

The basic problem is that the users of the subproject must be able to include subproject headers without seeing its `config.h` file. The most correct solution is to rename the `config.h` file into something unique, such as `foobar-config.h`. This is usually not feasible unless you are the maintainer of the subproject in question.

The pragmatic solution is to put the config header in a directory that has no other header files and then hide that from everyone else. One way is to create a top level subdirectory called `internal` and use that to build your own sources, like this:

```meson
subdir('internal') # create config.h in this subdir
internal_inc = include_directories('internal')
shared_library('foo', 'foo.c', include_directories : internal_inc)
```

Many projects keep their `config.h` in the top level directory that has no other source files in it. In that case you don't need to move it but can just do this instead:

```meson
internal_inc = include_directories('.') # At top level meson.build
```

## Make libraries buildable both as static and shared

Some platforms (e.g. iOS) requires linking everything in your main app statically. In other cases you might want shared libraries. They are also faster during development due to Meson's relinking optimization. However building both library types on all builds is slow and wasteful.

Your project should provide a toggle specifying which type of library it should build. As an example if you have a Meson option called `shared_lib` then you could do this:

```meson
if get_option('shared_lib')
  libtype = 'shared_library'
else
  libtype = 'static_library'
endif

mylib = build_target('foo', 'foo.c',
  target_type : libtype)
```

## Declare generated headers explicitly

Meson's Ninja backend works differently from Make and other systems. Rather than processing things directory per directory, it looks at the entire build definition at once and runs the individual compile jobs in what might look to the outside as a random order.

The reason for this is that this is much more efficient so your builds finish faster. The downside is that you have to be careful with your dependencies. The most common problem here is headers that are generated at compile time with e.g. code generators. If these headers are needed when building code that uses these libraries, the compile job might be run before the code generation step. The fix is to make the dependency explicit like this:

```meson
myheader = custom_target(...)
mylibrary = shared_library(...)
mydep = declare_dependency(link_with : mylibrary,
  include_directories : include_directories(...),
  sources : myheader)
```

And then you can use the dependency in the usual way:

```meson
executable('dep_using_exe', 'main.c',
  dependencies : mydep)
```

Meson will ensure that the header file has been built before compiling `main.c`.
