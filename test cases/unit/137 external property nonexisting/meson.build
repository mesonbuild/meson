project('missing property')

assert(meson.get_external_property('existing', native : get_option('native')) == '42')
message(meson.get_external_property('nonexisting', native : get_option('native')))
