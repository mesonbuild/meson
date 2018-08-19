project('myexe', 'c')
sub = subproject('sub')
prog = find_program('foobar')
custom1 = custom_target('custom1',
                        build_by_default : true,
                        input : [],
                        output : 'main1.c',
                        command : [prog, '@OUTPUT@'])
gen = generator(prog,
                output : '@BASENAME@.c',
                arguments : ['@OUTPUT@'])
custom2 = gen.process('main2.input')

executable('e1', custom1)
executable('e2', custom2)
