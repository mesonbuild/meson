project('Transitive flags', 'c')

# In a more realistic case, this would be a -I option from an external dependency
foo = declare_dependency(compile_args: '-DFOO=BAR')
libstaticdep = static_library('staticdep', 'dep.c', dependencies: foo)
executable('prog1', sources: files('prog.c'), link_with: libstaticdep)
executable('prog2', sources: files('prog.c'), link_whole: libstaticdep)

libshareddep = shared_library('shareddep', 'dep.c', dependencies: foo)
executable('prog3', sources: files('prog.c'), link_with: libshareddep)

staticdep = declare_dependency(link_with: libstaticdep)
executable('prog4', sources: files('prog.c'), dependencies: staticdep)
executable('prog5', sources: files('prog.c'), dependencies: staticdep.as_link_whole())

shareddep = declare_dependency(link_with: libshareddep)
executable('prog6', sources: files('prog.c'), dependencies: shareddep)
