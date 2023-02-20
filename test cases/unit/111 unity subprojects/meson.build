project('unity', 'c')


liba = subproject('a', default_options: ['unity=off']).get_variable('dep')
libb = subproject('b', default_options: ['unity=on']).get_variable('dep')
libc = subproject('c').get_variable('dep')

shared_library('mainlib', 
    ['a.c', 'b.c', 'c.c', 'd.c', 'e.c', 'f.c'],
    name_prefix: '',
    name_suffix: 's',
    dependencies: [liba, libb, libc])
