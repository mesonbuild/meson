project('feature module', meson_version : '>= 1.2.0')

feat = import('unstable-features')

new = feat.new('new', 'auto')

assert(new.auto(), 'new feature does not have correct value')
