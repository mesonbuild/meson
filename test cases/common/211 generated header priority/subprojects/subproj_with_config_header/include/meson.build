cdata = configuration_data()

cdata.set('STUFF_ONLY_THE_GENERATED_HEADER_DEFINES', 1)

configure_file(
  input : 'config.h.meson',
  output : 'config.h',
  configuration : cdata
)
