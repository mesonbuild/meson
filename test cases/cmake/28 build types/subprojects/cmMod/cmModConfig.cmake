# Check if meson correctly sets the build type and resolves the correct entry
add_library(cmMod::cmModLib++ STATIC IMPORTED)

set_property(TARGET cmMod::cmModLib++ PROPERTY MAP_IMPORTED_CONFIG_RELEASE IMPORTED_SPECIAL)
set_property(TARGET cmMod::cmModLib++ PROPERTY MAP_IMPORTED_CONFIG_DEBUG IMPORTED_SPECIAL)

# Do not take this
set_property(TARGET cmMod::cmModLib++ PROPERTY IMPORTED_LOCATION ${CMAKE_BINARY_DIR}/invalid.a)

# Take this
set_property(TARGET cmMod::cmModLib++ PROPERTY IMPORTED_LOCATION_IMPORTED_SPECIAL "${CMAKE_BINARY_DIR}/../libcmModLib_internal.a")
