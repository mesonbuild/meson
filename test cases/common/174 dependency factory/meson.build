project('dependency factory')

dep = dependency('gl', method: 'pkg-config', required: false)
if dep.found() and dep.type_name() == 'pkgconfig'
  dep.get_pkgconfig_variable('prefix')
endif
