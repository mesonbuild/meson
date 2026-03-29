project('a', 'c', meson_version: '>=1.11.0')

ssmod = import('sourceset')

a_lib = declare_dependency(link_with: [static_library('a', files('a.c'))])
b_lib = declare_dependency(link_with: [static_library('b', files('b.c'))])

ss = ssmod.source_set()
ss.add(files('main.c'))

ss.add(when: 'TRUE', if_true: [a_lib], if_false: [])
ss.add(when: 'FALSE', if_true: [], if_false: [b_lib])

ssconfig = ss.apply({'TRUE': true, 'FALSE': false})

executable(
    'exe',
    sources: ssconfig.sources(),
    dependencies: ssconfig.dependencies(),
)

