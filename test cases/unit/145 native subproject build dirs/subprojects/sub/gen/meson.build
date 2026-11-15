data = configuration_data()
data.set('for_machine', meson.is_cross_build() ? 1 : 0)
configure_file(input: 'gen.h.in', output: 'gen.h', build_subdir: 'sub2', configuration: data)
