project('answer', 'rust', default_options: ['rust_std=2021'])

rust = import('rust')

l = static_library('answer', 'src/lib.rs')
dep = declare_dependency(link_with: l)
meson.override_dependency('answer-2-rs', dep)
