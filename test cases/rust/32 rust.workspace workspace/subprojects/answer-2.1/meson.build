project('answer', 'rust', default_options: ['rust_std=2021'])

rust = import('rust')
cargo = rust.workspace()
assert(cargo.packages() == ['answer'])

answer_pkg = cargo.package()
assert(answer_pkg.all_features() == ['default', 'large'])
assert(answer_pkg.features() == ['default', 'large'])

l = static_library('answer', 'src/lib.rs', rust_args: ['--cfg', 'feature="large"'])
dep = declare_dependency(link_with: l)
meson.override_dependency('answer-2-rs', dep)
