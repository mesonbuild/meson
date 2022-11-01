project('relpath', 'c')

fs = import('fs')

assert(fs.relative_to('/prefix/lib/foo', '/prefix') == 'lib/foo', 'Path inside source is broken')
assert(fs.relative_to('/prefix/lib', '/prefix/bin') == '../lib', 'Path with common prefix with source is broken')
assert(fs.relative_to('/usr/lib/foo', '/usr/bin') == '../lib/foo', 'Path with common prefix with source is broken')

assert(fs.relative_to('/usr/lib/foo', '/usr/bin', within: '/usr') == '../lib/foo', 'Path with common prefix with source within "within" is broken')
assert(fs.relative_to('/usr/lib/foo', '/usr/bin', within: '/var') == '/usr/lib/foo', 'Path with common prefix with source outside "within" is broken')


