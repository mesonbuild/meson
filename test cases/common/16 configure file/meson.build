project('configure file test', 'c')

conf = configuration_data()

conf.set('var', 'mystring')
conf.set('other', 'string 2')
conf.set('second', ' bonus')
conf.set('BE_TRUE', true)

cfile = configure_file(input : 'config.h.in',
output : 'config.h',
configuration : conf)

e = executable('inctest', 'prog.c',
# Note that you should NOT do this. Don't add generated headers here
# This tests that we do the right thing even if people add in conf files
# to their sources.
cfile)
test('inctest', e)

# Now generate a header file with an external script.
genprog = find_program('python3')
scriptfile = '@0@/generator.py'.format(meson.current_source_dir())
ifile = '@0@/dummy.dat'.format(meson.current_source_dir())
ofile = '@0@/config2.h'.format(meson.current_build_dir())

configure_file(input : 'dummy.dat',
output : 'config2.h',
command : [genprog, scriptfile,  ifile, ofile],
install_dir : 'share/appdir')

test('inctest2', executable('prog2', 'prog2.c'))

# Generate a conf file without an input file.

dump = configuration_data()
dump.set_quoted('SHOULD_BE_STRING', 'string', description : 'A string')
dump.set_quoted('SHOULD_BE_STRING2', 'A "B" C')
dump.set_quoted('SHOULD_BE_STRING3', 'A "" C')
dump.set_quoted('SHOULD_BE_STRING4', 'A " C')
dump.set('SHOULD_BE_RETURN', 'return')
dump.set('SHOULD_BE_DEFINED', true)
dump.set('SHOULD_BE_UNDEFINED', false)
dump.set('SHOULD_BE_ONE', 1)
dump.set('SHOULD_BE_ZERO', 0, description : 'Absolutely zero')
dump.set('SHOULD_BE_QUOTED_ONE', '"1"')
configure_file(output : 'config3.h',
  configuration : dump)

test('Configless.', executable('dumpprog', 'dumpprog.c'))
