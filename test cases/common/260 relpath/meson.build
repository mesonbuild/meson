project('relpath', [])

fs = import('fs')

if host_machine.system() == 'windows'
  assert(fs.relative_to('c:\\proj1\\foo', 'c:\\proj1\\bar') == '..\\foo', 'Path with windows common prefix is broken')
  assert(fs.relative_to('c:\\proj1\\foo', 'd:\\proj1\\bar', within: 'd:\\') == 'c:\\proj1\\foo', 'windows path source outside "within" is broken')
else
  assert(fs.relative_to('/prefix/lib/foo', '/prefix') == 'lib/foo', 'Path inside source is broken')
  assert(fs.relative_to('/prefix/lib', '/prefix/bin') == '../lib', 'Path with common prefix with source is broken')
  assert(fs.relative_to('/usr/lib/foo', '/usr/bin') == '../lib/foo', 'Path with common prefix with source is broken')

  assert(fs.relative_to('/usr/lib/foo', '/usr/bin', within: '/usr') == '../lib/foo', 'Path with common prefix with source within "within" is broken')
  assert(fs.relative_to('/usr/lib/foo', '/usr/bin', within: '/var') == '/usr/lib/foo', 'Path with common prefix with source outside "within" is broken')
endif

