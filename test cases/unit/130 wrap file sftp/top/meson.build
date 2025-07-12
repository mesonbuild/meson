project('proj', 'c')

libfoo_proj = subproject('foo')
libfoo_dep = libfoo_proj.get_variable('libfoo_dep')

executable('doubler', 'doubler.c', dependencies: [libfoo_dep])
