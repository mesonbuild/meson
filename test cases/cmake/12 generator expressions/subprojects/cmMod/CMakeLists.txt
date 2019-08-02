cmake_minimum_required(VERSION 3.5)

project(cmMod)
set (CMAKE_CXX_STANDARD 14)

include(GNUInstallDirs)

add_library(cmModLib INTERFACE)

target_compile_options(cmModLib
  INTERFACE $<$<AND:$<CONFIG:Release>,$<CONFIG:Debug>>:-DCMAKE_FLAG_ERROR_A> # Check discard = false
  INTERFACE "-DCMAKE_FLAG_REQUIRED_A"
  INTERFACE $<$<AND:1,$<STREQUAL:asd,$<LOWER_CASE:AsD>>,$<NOT:$<EQUAL:4,2>>>:-DCMAKE_FLAG_REQUIRED_B>
  INTERFACE $<$<VERSION_LESS:1.2.3,2.1.0>:-DCMAKE_FLAG_REQUIRED_C>
)

target_include_directories(cmModLib INTERFACE
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>
)

target_compile_definitions(cmModLib INTERFACE -DCMAKE_COMPILER_DEFINE_STR="compDef")
