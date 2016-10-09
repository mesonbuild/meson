project('pathjoin', 'c')

assert(path_join('foo') == 'foo', 'Single argument join is broken')
assert(path_join('foo', 'bar') == 'foo/bar', 'Path joining is broken')
assert(path_join('foo', 'bar', 'baz') == 'foo/bar/baz', 'Path joining is broken')
assert(path_join('/foo', 'bar') == '/foo/bar', 'Path joining is broken')
assert(path_join('foo', '/bar') == '/bar', 'Absolute path joining is broken')
assert(path_join('/foo', '/bar') == '/bar', 'Absolute path joining is broken')

