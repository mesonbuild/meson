project('test')

if not add_languages('rust', required: false)
  error('MESON_SKIP_TEST test requires rust compiler')
endif

shared_library('test', 'foo.rs', rust_crate_type : 'staticlib')
