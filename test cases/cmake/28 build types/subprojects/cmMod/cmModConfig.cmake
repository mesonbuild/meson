# Check if meson correctly sets the build type and resolves the correct entry
add_library(cmMod::cmModLib++ STATIC IMPORTED)

get_target_property(CMMOD_LIB_DIR cmModLib_internal BINARY_DIR)
get_target_property(CMMOD_LIB_NAME cmModLib_internal NAME)
set(CMMOD_STATIC_LIB "${CMMOD_LIB_DIR}/../${CMAKE_STATIC_LIBRARY_PREFIX}${CMMOD_LIB_NAME}${CMAKE_STATIC_LIBRARY_SUFFIX}")

# Map both RELEASE and DEBUG to IMPORTED_SPECIAL
set_property(TARGET cmMod::cmModLib++ PROPERTY MAP_IMPORTED_CONFIG_RELEASE IMPORTED_SPECIAL)
set_property(TARGET cmMod::cmModLib++ PROPERTY MAP_IMPORTED_CONFIG_DEBUG IMPORTED_SPECIAL)

# Do not take this
set_property(TARGET cmMod::cmModLib++ PROPERTY IMPORTED_LOCATION ${CMAKE_BINARY_DIR}/invalid.a)

# Take this
set_property(TARGET cmMod::cmModLib++ PROPERTY IMPORTED_LOCATION_IMPORTED_SPECIAL ${CMMOD_STATIC_LIB})
