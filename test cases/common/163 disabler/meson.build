project('dolphin option', 'c')

d = disabler()

d2 = dependency(d)
d3 = (d == d2)
d4 = d + 0
d5 = d2 or true

has_not_changed = false
if is_disabler(d)
    has_not_changed = true
else
    has_not_changed = true
endif
assert(has_not_changed, 'Disabler has changed.')

assert(is_disabler(d), 'Disabler was not identified correctly.')
assert(is_disabler(d2), 'Function laundered disabler was not identified correctly.')
assert(is_disabler(d3), 'Disabler comparison should yield disabler.')
assert(is_disabler(d4), 'Disabler addition should yield disabler.')
assert(is_disabler(d5), 'Disabler logic op should yield disabler.')

assert(d, 'Disabler did not cause this to be skipped.')
assert(d2, 'Function laundered disabler did not cause this to be skipped.')
assert(d3, 'Disabler comparison should yield disabler and thus this would not be called.')
assert(d4, 'Disabler addition should yield disabler and thus this would not be called.')
assert(d5, 'Disabler logic op should yield disabler and thus this would not be called.')

number = 0

if d
  number = 1
else
  number = 2
endif

has_not_changed = false
if is_disabler(number)
    has_not_changed = true
else
    has_not_changed = true
endif
assert(has_not_changed, 'Number has changed.')

assert(not is_disabler(number), 'Number should not be a disabler.')
assert(number == 0, 'Plain if handled incorrectly, value should be 0 but is @0@'.format(number))

if d.found()
  number = 1
else
  number = 2
endif

assert(number == 2, 'If found handled incorrectly, value should be 2 but is @0@'.format(number))

dep = dependency('notfounddep', required : false, disabler : true)
app = executable('myapp', 'notfound.c', dependencies : [dep])
assert(is_disabler(app), 'App is not a disabler.')
app = executable('myapp', 'notfound.c', dependencies : [[dep]])
assert(is_disabler(app), 'App is not a disabler.')

cc = meson.get_compiler('c')
dep = cc.find_library('notfounddep', required : false, disabler : true)
app = executable('myapp', 'notfound.c', dependencies : [dep])
assert(is_disabler(app), 'App is not a disabler.')

dep = find_program('donotfindme', required : false, disabler : true)
app = executable('myapp', 'notfound.c', dependencies : [dep])
assert(is_disabler(app), 'App is not a disabler.')

has_not_changed = false
if is_disabler(app)
    has_not_changed = true
else
    has_not_changed = true
endif
assert(has_not_changed, 'App has changed.')
