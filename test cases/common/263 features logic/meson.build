project('feature logical test')

f_en = get_option('feature_en')
f_dis = get_option('feature_dis')
f_auto = get_option('feature_auto')

# Logical AND
assert((f_en and f_en).enabled())
assert((f_en and f_auto).enabled())
assert((f_en and f_dis).disabled())

assert((f_auto and f_en).enabled())
assert((f_auto and f_auto).auto())
assert((f_auto and f_dis).disabled())

assert((f_dis and f_en).disabled())
assert((f_dis and f_auto).disabled())
assert((f_dis and f_dis).disabled())

# Logical OR
assert((f_en or f_en).enabled())
assert((f_en or f_auto).enabled())
assert((f_en or f_dis).enabled())

assert((f_auto or f_en).enabled())
assert((f_auto or f_auto).auto())
assert((f_auto or f_dis).auto())

assert((f_dis or f_en).enabled())
assert((f_dis or f_auto).auto())
assert((f_dis or f_dis).disabled())

# Logical NOT
assert((not f_en).disabled())
assert((not f_auto).disabled())
assert((not f_dis).auto())
