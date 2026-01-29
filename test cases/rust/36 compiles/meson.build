project('rust compiles', 'rust')

rustc = meson.get_compiler('rust')

# Test that compiles() works without and with a main function
assert(rustc.compiles('pub fn foo() {}'), 'compiles() without main should work')
assert(rustc.compiles('pub fn main() {}'), 'compiles() with main should work')

# Test with a simple expression
assert(rustc.compiles('pub fn bar() { let _x: i32 = 1; }'), 'compiles() with simple code should work')

# Test that invalid code fails
assert(not rustc.compiles('pub fn baz() { invalid_syntax }'), 'compiles() should fail on invalid code')
