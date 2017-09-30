# Better support for prebuilt shared libraries

Meson has had support for prebuilt object files and static libraries.
This release adds feature parity to shared libraries. This means
that e.g. shipping prebuilt libraries as subprojects now can
be as simple as writing a definition file that looks like this.

    project('myprebuiltlibrary', 'c')
    
    cc = meson.get_compiler('c')
    prebuilt = cc.find_library('mylib', dirs : meson.current_source_dir())
    mydep = declare_dependency(include_directories : include_directories('.'),
                               dependencies : prebuilt)

Then you can use the dependency object in the same way as any other.
