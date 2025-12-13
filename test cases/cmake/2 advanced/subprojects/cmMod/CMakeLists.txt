cmake_minimum_required(VERSION ${CMAKE_VERSION})

project(cmMod)
set(CMAKE_CXX_STANDARD 14)

find_package(ZLIB REQUIRED)

include_directories(${CMAKE_CURRENT_BINARY_DIR} ${CMAKE_CURRENT_SOURCE_DIR} ${CMAKE_CURRENT_SOURCE_DIR}/lib)

set(CONFIG_OPT 42)
configure_file("config.h.in" "${CMAKE_CURRENT_BINARY_DIR}/config.h" @ONLY)

add_library(cmModLib       SHARED lib/cmMod.cpp)
add_library(cmModLibStatic STATIC lib/cmMod.cpp)
set_target_properties(cmModLibStatic PROPERTIES SOVERSION 1)
include(GenerateExportHeader)
generate_export_header(cmModLib)

set_target_properties(cmModLib PROPERTIES VERSION 1.0.1)

include(CheckLinkerFlag)
check_linker_flag(CXX "-Wl,--version-script=${CMAKE_CURRENT_SOURCE_DIR}/vers.map" HAS_VER_SCRIPT)
if(HAS_VER_SCRIPT)
  target_link_options(cmModLib PRIVATE
    "-Wl,--version-script=${CMAKE_CURRENT_SOURCE_DIR}/vers.map")
endif()

add_executable(testEXE main.cpp "${CMAKE_CURRENT_BINARY_DIR}/config.h")

target_link_libraries(cmModLib       ZLIB::ZLIB)
target_link_libraries(cmModLibStatic ;ZLIB::ZLIB;)
target_link_libraries(testEXE cmModLib)

if(APPLE)
  find_library(COREFOUNDATION_FRAMEWORK "CoreFoundation")
  if(NOT COREFOUNDATION_FRAMEWORK)
    message(FATAL_ERROR "CoreFoundation framework not found")
  endif()

  target_link_libraries(cmModLibStatic "${COREFOUNDATION_FRAMEWORK}")
  target_compile_definitions(cmModLibStatic PUBLIC USE_FRAMEWORK)
endif()

target_compile_definitions(cmModLibStatic PUBLIC CMMODLIB_STATIC_DEFINE)

install(TARGETS testEXE LIBRARY DESTINATION lib RUNTIME DESTINATION bin)
