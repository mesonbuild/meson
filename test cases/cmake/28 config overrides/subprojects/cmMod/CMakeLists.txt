cmake_minimum_required(VERSION 3.5)

project(cmMod)
set (CMAKE_CXX_STANDARD 14)

if(NOT ${CMAKE_BUILD_TYPE} STREQUAL "Release" AND NOT ${CMAKE_BUILD_TYPE} STREQUAL "Debug")
  message(FATAL_ERROR "CMAKE_BUILD_TYPE not set")
endif()

add_library(cmModLib_internal STATIC cmMod.cpp)

set(cmMod_DIR ${CMAKE_CURRENT_SOURCE_DIR})
find_package(cmMod CONFIG)

# This is the exported target, it comes from the config file
add_library(cmModLib++ INTERFACE)
target_link_libraries(cmModLib++ INTERFACE cmMod::cmModLib++)

# This is a standalone executable that uses one of the libraries
# It is a specific test that ensure deduping of '-L' arguments when
# the meson cmake interpreter uses the fileAPI to process the targets
add_executable(test2 test2.cpp)
target_link_libraries(test2 cmModLib2)
