project('configure file test', 'c')

conf = configuration_data()

conf.set('var', 'mystring')
conf.set('other', 'string 2')
conf.set('second', ' bonus')
conf.set('BE_TRUE', true)

assert(conf.get('var') == 'mystring', 'Get function is not working.')
assert(conf.get('var', 'default') == 'mystring', 'Get function is not working.')
assert(conf.get('notthere', 'default') == 'default', 'Default value getting is not working.')

cfile = configure_file(input : 'config.h.in',
output : 'config.h',
configuration : conf)

e = executable('inctest', 'prog.c',
# Note that you should NOT do this. Don't add generated headers here
# This tests that we do the right thing even if people add in conf files
# to their sources.
cfile)
test('inctest', e)

# Test if we can also pass files() as input
configure_file(input : files('config.h.in'),
               output : 'config2.h',
               configuration : conf)

# Now generate a header file with an external script.
genprog = import('python3').find_python()
scriptfile = '@0@/generator.py'.format(meson.current_source_dir())
ifile = '@0@/dummy.dat'.format(meson.current_source_dir())
ofile = '@0@/config2.h'.format(meson.current_build_dir())

check_file = find_program('check_file.py')
# Configure in source root with command and absolute paths
configure_file(input : 'dummy.dat',
  output : 'config2.h',
  command : [genprog, scriptfile,  ifile, ofile],
  install_dir : 'share/appdir')
run_command(check_file, join_paths(meson.current_build_dir(), 'config2.h'))

# Same again as before, but an input file should not be required in
# this case where we use a command/script to generate the output file.
genscript2b = '@0@/generator-without-input-file.py'.format(meson.current_source_dir())
ofile2b = '@0@/config2b.h'.format(meson.current_build_dir())
configure_file(
  output : 'config2b.h',
  command : [genprog, genscript2b, ofile2b],
  install_dir : 'share/appdir')
run_command(check_file, join_paths(meson.current_build_dir(), 'config2b.h'))

found_script = find_program('generator.py')
# More configure_file tests in here
subdir('subdir')

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


# Config file generation in a loop with @BASENAME@ substitution
dump = configuration_data()
dump.set('ZERO', 0)
config_templates = files(['config4a.h.in', 'config4b.h.in'])
foreach config_template : config_templates
  configure_file(input : config_template, output : '@BASENAME@',
                 configuration : dump)
endforeach

test('Substituted', executable('prog4', 'prog4.c'))

# Test `capture` keyword

basename_py = find_program('basename.py')
file_contains_py = find_program('file_contains.py')
test_string = 'hello world'
test_input_file = join_paths(meson.current_build_dir(), test_string)
run_command(find_program('touch.py'), test_input_file)
configs = [
    # no input
    configure_file(command: [ basename_py, test_string ], capture: true, output: 'capture test 1'),
    # with input
    configure_file(input: test_input_file, command: [ basename_py, '@INPUT@' ], capture: true, output: 'capture test 2'),
]
foreach c : configs
    test('@0@'.format(c), file_contains_py, args: [ c, test_string ])
endforeach
