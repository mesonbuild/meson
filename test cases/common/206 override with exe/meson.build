project('myexe', 'c')
sub = subproject('sub')
prog = find_program('foobar')
custom_target('custom',
              build_by_default : true,
              input : [],
              output : 'custom',
              command : [prog, '@OUTPUT@'])
