project('relpath', [])

fs = import('fs')

if host_machine.system() == 'windows'
  assert(fs.relative_to('c:\\proj1\\foo', 'c:\\proj1\\bar') == '..\\foo', 'Path with windows common prefix is broken')
  #expect_error(fs.relative_to('c:\\proj1\\foo', 'd:\\proj1\\bar') == 'c:\\proj1\\foo', 'Error was expected because relative path does not exist')
  #expect_error(fs.relative_to('c:\\proj1\\foo', 'c:\\proj2\\bar', if_within: 'c:\\proj2'), 'Error expected, path1 is outside `if_within`)
  assert(fs.relative_to('c:\\proj1\\foo', 'd:\\proj1\\bar', allow_absolute: true) == 'c:\\proj1\\foo', 'Path falls back if allow absolute is true')
  assert(fs.relative_to('c:\\proj1\\foo', 'c:\\proj2\\bar', if_within: 'c:\\proj2', allow_absolute: true) == 'c:\\proj1\\foo', 'Path falls back to path1 if allow_absolute is True')
else
  assert(fs.relative_to('/prefix/lib/foo', '/prefix') == 'lib/foo', 'Path inside source is broken')
  assert(fs.relative_to('/prefix/lib', '/prefix/bin') == '../lib', 'Path with common prefix with source is broken')
  assert(fs.relative_to('/usr/lib/foo', '/usr/bin') == '../lib/foo', 'Path with common prefix with source is broken')
  assert(fs.relative_to('/usr/lib/foo', '/usr/bin', if_within: '/usr') == '../lib/foo', 'Path with common prefix using `if_within` is broken')
  #expect_error(fs.relative_to('/project1/lib/foo', '/usr/bin', if_within: '/usr'), 'Expected error because /project1 is not in /usr')  
  assert(fs.relative_to('/project1/lib/foo', '/usr/bin', if_within: '/usr', allow_absolute: true) == '/project1/lib/foo', 'Expected path1 because allow_absolute is true')
endif

