project('suba', 'c')

liba = shared_library('liba', ['g.c', 'h.c', 'i.c', 'j.c', 'k.c', 'l.c'],
    name_prefix: '',
    name_suffix: 's',
)

dep = declare_dependency(link_with: [liba])
