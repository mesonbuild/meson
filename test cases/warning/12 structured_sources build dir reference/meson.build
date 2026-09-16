project('structured_sources build dir reference')

gen = configure_file(input : 'in.rs', output : 'gen.rs', copy : true)
structured_sources([meson.current_build_dir() / 'gen.rs'])
