project('install tag', 'c')

subdir('subdir')

# Those files should not be tagged
configure_file(input: 'foo.in', output: 'foo-notag.h',
  configuration: {'foo': 'bar'},
  install_dir: get_option('datadir'),
  install: true,
)
install_data('bar-notag.txt',
  install_dir: get_option('datadir')
)
custom_target('ct1',
  output: ['out1-notag.txt', 'out2-notag.txt'],
  command: ['script.py', '@OUTPUT@'],
  install_dir: get_option('datadir'),
  install: true,
)

# Those files should be tagged as devel
install_headers('foo1-devel.h')
install_data('bar-devel.h',
  install_dir: get_option('includedir'),
)
configure_file(input: 'foo.in', output: 'foo2-devel.h',
  configuration: {'foo': 'bar'},
  install_dir: get_option('includedir'),
  install: true,
)
static_library('static', 'lib.c',
  install: true,
)

# Those files should have 'runtime' tag
executable('app', 'main.c',
  install: true,
)
shared_library('shared', 'lib.c',
  install: true,
)
both_libraries('both', 'lib.c',
  install: true,
)

# Those files should have custom tag
install_data('bar-custom.txt',
  install_dir: get_option('datadir'),
  install_tag: 'custom')
configure_file(input: 'foo.in', output: 'foo-custom.h',
  configuration: {'foo': 'bar'},
  install_dir: get_option('datadir'),
  install_tag: 'custom',
  install: true,
)
both_libraries('bothcustom', 'lib.c',
  install_tag: 'custom',
  install: true,
)
custom_target('ct2',
  output: ['out1-custom.txt', 'out2-custom.txt'],
  command: ['script.py', '@OUTPUT@'],
  install_dir: get_option('datadir'),
  install_tag: 'custom',
  install: true,
)
install_subdir('custom_files',
  install_dir: get_option('datadir'),
  install_tag: 'custom',
)

# First is custom, 2nd is devel, 3rd has no tag
custom_target('ct3',
  output: ['out3-custom.txt', 'out-devel.h', 'out3-notag.txt'],
  command: ['script.py', '@OUTPUT@'],
  install_dir: [get_option('datadir'), get_option('includedir'), get_option('datadir')],
  install_tag: ['custom', 'devel', false],
  install: true,
)

meson.add_install_script('script.py', install_tag: 'custom')
meson.add_install_script('script.py')
