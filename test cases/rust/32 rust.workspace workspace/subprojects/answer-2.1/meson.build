project('answer', 'rust', default_options: ['rust_std=2021'])

rust = import('rust')
cargo_ws = rust.workspace()
assert(cargo_ws.packages() == ['answer'])

l = static_library('answer', 'src/lib.rs', rust_args: ['--cfg', 'feature="large"'])
dep = declare_dependency(link_with: l)
meson.override_dependency('answer-2-rs', dep)
