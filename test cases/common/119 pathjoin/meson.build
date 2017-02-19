project('pathjoin', 'c')

# Test string-args form since that is the canonical way
assert(join_paths('foo') == 'foo', 'Single argument join is broken')
assert(join_paths('foo', 'bar') == 'foo/bar', 'Path joining is broken')
assert(join_paths('foo', 'bar', 'baz') == 'foo/bar/baz', 'Path joining is broken')
assert(join_paths('/foo', 'bar') == '/foo/bar', 'Path joining is broken')
assert(join_paths('foo', '/bar') == '/bar', 'Absolute path joining is broken')
assert(join_paths('/foo', '/bar') == '/bar', 'Absolute path joining is broken')

# Test array form since people are using that too
assert(join_paths(['foo']) == 'foo', 'Single argument join is broken')
assert(join_paths(['foo', 'bar']) == 'foo/bar', 'Path joining is broken')
assert(join_paths(['foo', 'bar', 'baz']) == 'foo/bar/baz', 'Path joining is broken')
assert(join_paths(['/foo', 'bar']) == '/foo/bar', 'Path joining is broken')
assert(join_paths(['foo', '/bar']) == '/bar', 'Absolute path joining is broken')
assert(join_paths(['/foo', '/bar']) == '/bar', 'Absolute path joining is broken')
