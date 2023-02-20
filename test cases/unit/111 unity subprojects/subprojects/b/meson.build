project('subb', 'c')

libb = shared_library('libb', ['m.c', 'n.c', 'o.c', 'p.c', 'q.c', 'r.c', 's.c'],
    name_prefix: '',
    name_suffix: 's',
)

dep = declare_dependency(link_with: [libb])
