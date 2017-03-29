# Shipping prebuilt binaries as wraps

A common dependency case, especially on Windows, is the need to provide dependencies as prebuilt binaries rather than Meson projects that you build from scratch. Common reasons include not having access to source code, not having the time and effort to rewrite a legacy system's build definitions to Meson or just the fact that compiling the dependency projects takes too long.

Packaging a project is straightforward. As an example let's look at a case where the project consists of one static library called `bob` and some headers. To create a binary dependency project we put the static library at the top level and headers in a subdirectory called `include`. The Meson build definition would look like the following.

```meson
project('binary dep', 'c')

cc = meson.get_compiler('c')
bin_dep = declare_dependency(
  dependencies : cc.find_library('bob', dirs : meson.current_source_dir()),
  include_directories : include_directories('include'))
```

Now you can use this subproject as if it was a Meson project:

```meson
project('using dep', 'c')
bob_dep = subproject('bob').get_variable('bin_dep')
executable('prog', 'prog.c', dependencies : bob_dep)
```

Note that often libraries compiled with different compilers (or even compiler flags) might not be compatible. If you do this, then you are responsible for verifying that your libraries are compatible, Meson will not check things for you.
