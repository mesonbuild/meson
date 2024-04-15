# Check if meson correctly sets the build type and resolves the correct entry
add_library(cmMod::cmModLib++ STATIC IMPORTED)

# Do not take this
set_property(TARGET cmMod::cmModLib++ PROPERTY IMPORTED_LOCATION ${CMAKE_BINARY_DIR}/invalid.a)

# Take one of these
set_property(TARGET cmMod::cmModLib++ PROPERTY IMPORTED_LOCATION_RELEASE "${CMAKE_BINARY_DIR}/../libcmModLib_internal.a")
set_property(TARGET cmMod::cmModLib++ PROPERTY IMPORTED_LOCATION_DEBUG "${CMAKE_BINARY_DIR}/../libcmModLib_internal.a")
