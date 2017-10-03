# Better support for shared libraries in non-system paths

Meson has had support for prebuilt object files and static libraries.
This release adds feature parity to shared libraries that are either
in non-standard system paths or shipped as part of your project. On
systems that support rpath, Meson automatically adds rpath entries
to built targets using manually found external libraries.

This means that e.g. supporting prebuilt libraries shipped with your
source or provided by subprojects or wrap definitions by writing a
build file like this:

    project('myprebuiltlibrary', 'c')
    
    cc = meson.get_compiler('c')
    prebuilt = cc.find_library('mylib', dirs : meson.current_source_dir())
    mydep = declare_dependency(include_directories : include_directories('.'),
                               dependencies : prebuilt)

Then you can use the dependency object in the same way as any other.
