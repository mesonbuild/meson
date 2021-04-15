project('myexe', 'c', version: '0.1')
sub = subproject('sub')

prog = find_program('foobar', version : '>= 2.0', required : false, native : true)
assert(not prog.found())

prog = find_program('foobar', version : '>= 1.0', native : true)

if meson.is_cross_build()
  prog_for_host = find_program('foobar', version : '>= 1.0', native : false, required : false)
  assert(not prog_for_host.found(), 'got build machine binary for host machine!')

  prog_forced = find_program('foobar2', native : false)
  assert(prog_forced.found())
else
  prog_for_host = find_program('foobar', version : '>= 1.0', native : false, required : false)
  assert(prog_for_host.found(), 'host and build are the same, should have been found')
endif

custom1 = custom_target('custom1',
                        build_by_default : true,
                        input : [],
                        output : 'main1.c',
                        command : [prog, '@OUTPUT@'])
gen = generator(prog,
                output : '@BASENAME@.c',
                arguments : ['@OUTPUT@'])
custom2 = gen.process('main2.input')

message(prog.full_path())

executable('e1', custom1)
executable('e2', custom2)
