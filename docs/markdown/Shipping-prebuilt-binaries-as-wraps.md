# Shipping prebuilt binaries as wraps

A common dependency case, especially on Windows, is the need to
provide dependencies as prebuilt binaries rather than Meson projects
that you build from scratch. Common reasons include not having access
to source code, not having the time and effort to rewrite a legacy
system's build definitions to Meson or just the fact that compiling
the dependency projects takes too long.

Packaging a project is straightforward. As an example let's look at a
case where the project consists of one static library called `bob` and
some headers. To create a binary dependency project we put the static
library at the top level and headers in a subdirectory called
`include`. The Meson build definition would look like the following.

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

Note that often libraries compiled with different compilers (or even
compiler flags) might not be compatible. If you do this, then you are
responsible for verifying that your libraries are compatible, Meson
will not check things for you.

## Note for Linux libraries

A precompiled linux shared library (.so) requires a soname field to be properly installed. If the soname field is missing, binaries referencing the library will require a hard link to the location of the library at install time (`/path/to/your/project/subprojects/precompiledlibrary/lib.so` instead of `$INSTALL_PREFIX/lib/lib.so`) after installation.

You should change the compilation options for the precompiled library to avoid this issue. If recompiling is not an option, you can use the [patchelf](https://github.com/NixOS/patchelf) tool with the command `patchelf --set-soname libfoo.so libfoo.so` to edit the precompiled library after the fact.

Meson generally guarantees any library it compiles has a soname. One notable exception is libraries built with the [[shared_module]] function.
