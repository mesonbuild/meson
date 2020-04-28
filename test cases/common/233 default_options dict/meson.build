project(
  'default_options dict',
  'c', 'cpp',
  default_options : {'c_std': 'c99', 'cpp_std': 'c++98'}
)

executable(
  'overriden',
  'override.cpp',
  override_options : {'cpp_std' : 'c++14'},
)

subproject('1', default_options : {'default_library': 'both'}).get_variable('exe1')

dependency('zlib', default_options : {'default_library': 'both'})
