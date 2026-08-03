project('rust pkgconfig proc-macro', 'rust')

rust = import('rust')
pkgconfig = import('pkgconfig')

pm = rust.proc_macro('proc_macro_examples', 'pm.rs')

staticlib = static_library(
    'staticlib',
    'lib.rs',
    link_with: pm,
    rust_dependency_map: {'proc_macro_examples': 'proc_macro_examples'},
)

pkgconfig.generate(
    staticlib,
    name: 'staticlib',
    filebase: 'staticlib',
    description: 'static library using a proc-macro',
)

test(
    'pkgconfig-proc-macro-check-uninstalled',
    find_program('check_pc.py'),
    args: [
        join_paths(meson.current_build_dir(), 'meson-uninstalled', 'staticlib-uninstalled.pc'),
    ],
)
test(
    'pkgconfig-proc-macro-check',
    find_program('check_pc.py'),
    args: [
        join_paths(meson.current_build_dir(), 'meson-private', 'staticlib.pc'),
    ],
)
