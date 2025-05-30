project('cargo features options')

rust = import('rust')
rust.add_cargo_features('f1')

# We should only have f1 and f2, see test.json.
d = dependency('foo-1-rs')
features = d.get_variable('features').split(',')
assert(features.length() == 2)
assert('f1' in features)
assert('f2' in features)

