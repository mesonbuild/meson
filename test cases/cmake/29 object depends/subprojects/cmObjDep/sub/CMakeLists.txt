gen_header(subdir)

# OBJECT_DEPENDS relative to this directory, not to the top level one
set_source_files_properties(
  subdir.c
  PROPERTIES OBJECT_DEPENDS "${CMAKE_CURRENT_BINARY_DIR}/subdir.h")

add_library(cmObjDepSub STATIC subdir.c)
target_include_directories(cmObjDepSub PRIVATE ${CMAKE_CURRENT_BINARY_DIR})
