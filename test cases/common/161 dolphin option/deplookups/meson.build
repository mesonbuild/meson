exist_auto = dependency('zlib', options : 'auto_opt')
exist_req = dependency('zlib', options : 'req_opt')
exist_disable = dependency('zlib', options : 'dis_opt')

copy_of_exist_disable = exist_disable

not_exist_auto = dependency('nonexist', options : 'auto_opt')
# This is not valid because it would fail execution.
# This combination is tested in a failing test.
#not_exist_req = dependency('nonexist', options : 'req_opt')
not_exist_disable = dependency('nonexist', options : 'dis_opt')

assert(exist_auto.found(), 'Zlib not found')
assert(exist_req.found(), 'Zlib not found')
assert(not exist_disable.found(), 'A disabled dependency claims to be found.')
assert(not copy_of_exist_disable.found(), 'A copied disabled dependency works incorrectly.')

assert(not not_exist_auto.found(), 'Nonexisting dependency was found.')
assert(not not_exist_disable.found(), 'Nonexisting dependency was found.')

