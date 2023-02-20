project('subc', 'c')

libc = shared_library('libc', ['t.c', 'u.c', 'v.c', 'w.c', 'x.c', 'y.c'],
    name_prefix: '',
    name_suffix: 's',
)

dep = declare_dependency(link_with: [libc])
