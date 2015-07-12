entity_lib = static_library('entity', 'entity1.c')

entity_dep = declare_dependency(link_with : entity_lib,
  include_directories : include_directories('.'),
  sources : 'entity2.c')
