project('feature user option', 'c')

feature_opts = get_option('auto_features')
required_opt = get_option('required')
optional_opt = get_option('optional')
disabled_opt = get_option('disabled')

assert(not feature_opts.enabled(), 'Should be auto option')
assert(not feature_opts.disabled(), 'Should be auto option')
assert(feature_opts.auto(), 'Should be auto option')

assert(required_opt.enabled(), 'Should be enabled option')
assert(not required_opt.disabled(), 'Should be enabled option')
assert(not required_opt.auto(), 'Should be enabled option')

assert(not optional_opt.enabled(), 'Should be auto option')
assert(not optional_opt.disabled(), 'Should be auto option')
assert(optional_opt.auto(), 'Should be auto option')

assert(not disabled_opt.enabled(), 'Should be disabled option')
assert(disabled_opt.disabled(), 'Should be disabled option')
assert(not disabled_opt.auto(), 'Should be disabled option')

dep = dependency('threads', required : required_opt)
assert(dep.found(), 'Should find required "threads" dep')

dep = dependency('threads', required : optional_opt)
assert(dep.found(), 'Should find optional "threads" dep')

dep = dependency('threads', required : disabled_opt)
assert(not dep.found(), 'Should not find disabled "threads" dep')

dep = dependency('notfounddep', required : optional_opt)
assert(not dep.found(), 'Should not find optional "notfounddep" dep')

dep = dependency('notfounddep', required : disabled_opt)
assert(not dep.found(), 'Should not find disabled "notfounddep" dep')

cc = meson.get_compiler('c')
lib = cc.find_library('m', required : disabled_opt)
assert(not lib.found(), 'Should not find "m" library')

cp = find_program('cp', required : disabled_opt)
assert(not cp.found(), 'Should not find "cp" program')

found = add_languages('cpp', required : disabled_opt)
assert(not found, 'Should not find "cpp" language')
