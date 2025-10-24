project('answer', 'rust', default_options: ['rust_std=2021'])

rust = import('rust')
cargo_ws = rust.workspace()
assert(cargo_ws.packages() == ['answer'])

answer_pkg = cargo_ws.package()
assert(answer_pkg.all_features() == ['default', 'large'])
assert(answer_pkg.features() == ['default', 'large'])

l = static_library('answer', 'src/lib.rs',
                   rust_args: answer_pkg.rust_args(),
                   rust_dependency_map: answer_pkg.rust_dependency_map())
dep = declare_dependency(link_with: l)
meson.override_dependency('answer-2-rs', dep)
