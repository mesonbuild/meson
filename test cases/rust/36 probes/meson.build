project('rust compiles', 'rust')

rustc = meson.get_compiler('rust')

# Test that compiles() works without and with a main function
assert(rustc.compiles('pub fn foo() {}'), 'compiles() without main should work')
assert(rustc.compiles('pub fn main() {}'), 'compiles() with main should work')

# Test with a simple expression
assert(rustc.compiles('pub fn bar() { let _x: i32 = 1; }'), 'compiles() with simple code should work')

# Test that invalid code fails
assert(not rustc.compiles('pub fn baz() { invalid_syntax }'), 'compiles() should fail on invalid code')


rustmod = import('rust')

cargo_target = rustmod.compiler_target()
message('Host Rust target triple: ' + cargo_target)
assert(cargo_target != '', 'compiler_target() should return a non-empty string')
assert(cargo_target == rustmod.compiler_target(native: false), 'compiler_target(native: false) should match the default')
assert(cargo_target.contains('-'), 'compiler_target() should return a triple containing dashes')

cargo_host = rustmod.compiler_target(native: true)
message('Build Rust target triple: ' + cargo_host)
assert(cargo_host != '', 'compiler_target(native: true) should return a non-empty string')
assert(cargo_host.contains('-'), 'compiler_target(native: true) should return a triple containing dashes')
