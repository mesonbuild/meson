project('cargo build-dependency both machines', 'rust', meson_version: '>= 1.13')

rust = import('rust')

# "tool" is reachable only through an always-false [target] build-dependency of
# "app"; it is requested explicitly and therefore built for the build machine.
cargo = rust.workspace(extra_members: ['tool'])

assert(cargo.packages() == ['app', 'shared', 'tool'])

subdir('shared')
subdir('tool')
subdir('app')
