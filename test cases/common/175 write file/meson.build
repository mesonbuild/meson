project('write file test', 'cpp')

# Change this to see the file rebuilt
content = '\n'.join([
  '#pragma once',
  '#include <string>',
  'static const std::string test_value = "this is the new value";',
  '// new line to force rebuild',
])

write_file(
  output: 'test_writefile.h',
  text: content,
  install_dir: get_option('datadir'),
  install: false
)

executable('testexe',
  'should_not_rebuild.cpp',
  include_directories: [ include_directories('.'), ],
)
