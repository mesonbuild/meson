project('fs module test')

fs = import('fs')

assert(fs.exists('meson.build'), 'Existing file reported as missing.')
assert(not fs.exists('nonexisting'), 'Nonexisting file was found.')

if build_machine.system() != 'windows' and build_machine.system() != 'cygwin'
  assert(fs.is_symlink('a_symlink'), 'Symlink not detected.')
  assert(not fs.is_symlink('meson.build'), 'Regular file detected as symlink.')
endif

assert(fs.is_file('meson.build'), 'File not detected as a file.')
assert(not fs.is_file('subprojects'), 'Directory detected as a file.')
assert(not fs.is_file('nonexisting'), 'Bad path detected as a file.')

assert(fs.is_dir('subprojects'), 'Dir not detected correctly.')
assert(not fs.is_dir('meson.build'), 'File detected as a dir.')
assert(not fs.is_dir('nonexisting'), 'Bad path detected as a dir.')

assert(fs.is_dir('~'), 'expanduser not working')
assert(not fs.is_file('~'), 'expanduser not working')

original = 'foo.txt'
new = fs.with_suffix(original, '.ini')
assert(new.endswith('foo.ini') and not new.contains('.txt'), 'with_suffix failed')

if build_machine.system() != 'windows'
  # this feature works on Windows, but `/` on windows is interpreted like `.drive` which in general may not be `c:/`
  # so we omit this from self-test on Windows

  original = '/opt/foo.txt'
  new = fs.with_suffix(original, '.ini')
  assert(new == '/opt/foo.ini', 'absolute path with_suffix failed')
endif

subdir('subdir')
