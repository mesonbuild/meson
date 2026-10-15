cmake_minimum_required(VERSION ${CMAKE_VERSION})

project(cmObjDep C)

include_directories(${CMAKE_CURRENT_BINARY_DIR})

# Generate <name>.h in several steps, so a lost compile-order dependency cannot
# win the race against the compile of the source including the header.
function(gen_header name)
  add_custom_command(
    OUTPUT  "${CMAKE_CURRENT_BINARY_DIR}/${name}.step1"
    COMMAND ${CMAKE_COMMAND} -E copy "${CMAKE_CURRENT_SOURCE_DIR}/${name}.h.in" "${CMAKE_CURRENT_BINARY_DIR}/${name}.step1"
    DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/${name}.h.in"
  )
  add_custom_command(
    OUTPUT  "${CMAKE_CURRENT_BINARY_DIR}/${name}.step2"
    COMMAND ${CMAKE_COMMAND} -E copy "${CMAKE_CURRENT_BINARY_DIR}/${name}.step1" "${CMAKE_CURRENT_BINARY_DIR}/${name}.step2"
    DEPENDS "${CMAKE_CURRENT_BINARY_DIR}/${name}.step1"
  )
  add_custom_command(
    OUTPUT  "${CMAKE_CURRENT_BINARY_DIR}/${name}.step3"
    COMMAND ${CMAKE_COMMAND} -E copy "${CMAKE_CURRENT_BINARY_DIR}/${name}.step2" "${CMAKE_CURRENT_BINARY_DIR}/${name}.step3"
    DEPENDS "${CMAKE_CURRENT_BINARY_DIR}/${name}.step2"
  )
  add_custom_command(
    OUTPUT  "${CMAKE_CURRENT_BINARY_DIR}/${name}.h"
    COMMAND ${CMAKE_COMMAND} -E copy "${CMAKE_CURRENT_BINARY_DIR}/${name}.step3" "${CMAKE_CURRENT_BINARY_DIR}/${name}.h"
    DEPENDS "${CMAKE_CURRENT_BINARY_DIR}/${name}.step3"
  )
  add_custom_target(gen_${name} DEPENDS "${CMAKE_CURRENT_BINARY_DIR}/${name}.h")
endfunction()

gen_header(absolute)
gen_header(relative)
gen_header(transitive)

# OBJECT_DEPENDS with an absolute source path
set_source_files_properties(
  "${CMAKE_CURRENT_SOURCE_DIR}/absolute.c"
  PROPERTIES OBJECT_DEPENDS "${CMAKE_CURRENT_BINARY_DIR}/absolute.h")
add_library(cmObjDepAbsolute STATIC absolute.c)

# OBJECT_DEPENDS with a path relative to the current source directory
set_source_files_properties(
  relative.c
  PROPERTIES OBJECT_DEPENDS "${CMAKE_CURRENT_BINARY_DIR}/relative.h")
add_library(cmObjDepRelative STATIC relative.c)

# transitive.c reaches gen_transitive only through the library it links against
add_library(cmObjDepProvider STATIC provider.c)
add_dependencies(cmObjDepProvider gen_transitive)

add_library(cmObjDepTransitive STATIC transitive.c)
target_link_libraries(cmObjDepTransitive PUBLIC cmObjDepProvider)

add_subdirectory(sub)
