# Construct the name of the library that was built
# (cmake in meson does not support TARGET_FILE generator expression unless the target is imported)
get_target_property(CMMOD_LIB_DIR cmModLib_internal BINARY_DIR)
get_target_property(CMMOD_LIB_NAME cmModLib_internal NAME)

# meson Windows static library naming scheme
if(MSVC)
  set(CMMOD_LIB_PREFIX lib)
  set(CMMOD_LIB_SUFFIX .a)
else()
  set(CMMOD_LIB_PREFIX ${CMAKE_STATIC_LIBRARY_PREFIX})
  set(CMMOD_LIB_SUFFIX ${CMAKE_STATIC_LIBRARY_SUFFIX})
endif()

# Check if meson correctly sets the build type and resolves the correct entry
add_library(cmMod::cmModLib++ STATIC IMPORTED)

set(CMMOD_STATIC_LIB "${CMMOD_LIB_DIR}/../${CMMOD_LIB_PREFIX}${CMMOD_LIB_NAME}${CMMOD_LIB_SUFFIX}")

# Map both RELEASE and DEBUG to IMPORTED_SPECIAL
set_property(TARGET cmMod::cmModLib++ PROPERTY MAP_IMPORTED_CONFIG_RELEASE IMPORTED_SPECIAL)
set_property(TARGET cmMod::cmModLib++ PROPERTY MAP_IMPORTED_CONFIG_DEBUG IMPORTED_SPECIAL)

# Do not take this
set_property(TARGET cmMod::cmModLib++ PROPERTY IMPORTED_LOCATION ${CMAKE_BINARY_DIR}/invalid.a)

# Take this
set_property(TARGET cmMod::cmModLib++ PROPERTY IMPORTED_LOCATION_IMPORTED_SPECIAL ${CMMOD_STATIC_LIB})
set_property(TARGET cmMod::cmModLib++ PROPERTY INTERFACE_INCLUDE_DIRECTORIES ${CMAKE_CURRENT_SOURCE_DIR}/include)

# Another name for the same library as interface, so that meson cmake uses
# the fileAPI to process it - it checks that '-L' arguments are not duped
# and that non-target libraries are correctly resolved
add_library(cmModLib2 INTERFACE)
set_property(TARGET cmModLib2 PROPERTY INTERFACE_LINK_LIBRARIES -l${CMMOD_LIB_NAME})
set_property(TARGET cmModLib2 PROPERTY INTERFACE_LINK_DIRECTORIES ${CMMOD_LIB_DIR}/..)
set_property(TARGET cmModLib2
  APPEND PROPERTY INTERFACE_INCLUDE_DIRECTORIES
  $<$<CONFIG:Release>:${CMAKE_CURRENT_SOURCE_DIR}/include>)
set_property(TARGET cmModLib2
  APPEND PROPERTY INTERFACE_INCLUDE_DIRECTORIES
  $<$<CONFIG:Debug>:${CMAKE_CURRENT_SOURCE_DIR}/include>)

# Yet another name for the same library, it checks target_link_directories
add_library(cmModLib3 INTERFACE)
target_link_libraries(cmModLib3 INTERFACE -l${CMMOD_LIB_NAME})
target_link_directories(cmModLib3 INTERFACE ${CMMOD_LIB_DIR}/..)
target_include_directories(cmModLib3 INTERFACE ${CMAKE_CURRENT_SOURCE_DIR}/include)
