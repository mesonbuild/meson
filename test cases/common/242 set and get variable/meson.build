project('set and get')

var1 = 'test1.txt'
var2 = files('test1.txt')

# Use is_disabler for accessing variables
assert(var1 == 'test1.txt')
assert(not is_disabler(var2))

# Ensure that set variables behave correctly
set_variable('var3', 'test2.txt')
set_variable('var4', files('test2.txt'))

assert(var3 == 'test2.txt')
assert(not is_disabler(var4))

# Test get_variable directly
assert(get_variable('var1') == 'test1.txt')
assert(not is_disabler(get_variable('var2')))
assert(get_variable('var3') == 'test2.txt')
assert(not is_disabler(get_variable('var4')))

# Test get_variable indirectly

var5 = get_variable('var1')
var6 = get_variable('var2')
var7 = get_variable('var3')
var8 = get_variable('var4')
set_variable('var9', get_variable('var7'))
set_variable('var0', get_variable('var8'))

assert(var5 == 'test1.txt')
assert(not is_disabler(var6))
assert(var7 == 'test2.txt')
assert(not is_disabler(var8))
assert(get_variable('var9') == 'test2.txt')
assert(not is_disabler(get_variable('var0')))
