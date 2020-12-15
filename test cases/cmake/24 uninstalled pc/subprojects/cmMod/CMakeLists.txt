cmake_minimum_required(VERSION 3.5)

project(cmMod)
set (CMAKE_CXX_STANDARD 14)

include_directories(${CMAKE_CURRENT_BINARY_DIR})

find_package(PkgConfig REQUIRED)
pkg_check_modules(MY_PKG REQUIRED IMPORTED_TARGET libPCTest42)

function(fix_path_spaces)
  set(TMP)
  set(RES)

  foreach(I IN LISTS ${ARGV0})
    if("${I}" MATCHES "^/.*$" OR "${I}" MATCHES "^[a-zA-Z]:/$")
      list(APPEND RES "${TMP}")
      set(TMP "${I}")
    else()
      set(TMP "${TMP} ${I}")
    endif()
  endforeach()

  if(NOT "${TMP}" STREQUAL "")
    list(APPEND RES "${TMP}")
  endif()
  set(${ARGV0} "${RES}" PARENT_SCOPE)
endfunction(fix_path_spaces)


#list(JOIN MY_PKG_LIBRARY_DIRS " " MY_PKG_LIBRARY_DIRS)
fix_path_spaces(MY_PKG_LIBRARY_DIRS)
fix_path_spaces(MY_PKG_INCLUDE_DIRS)

set(LIBRARIES "${MY_PKG_LIBRARY_DIRS}/${CMAKE_STATIC_LIBRARY_PREFIX}${MY_PKG_LIBRARIES}${CMAKE_STATIC_LIBRARY_SUFFIX}")

add_definitions("-DDO_NOTHING_JUST_A_FLAG=1")

add_library(cmModLib++ SHARED cmMod.cpp)
target_compile_definitions(cmModLib++ PRIVATE MESON_MAGIC_FLAG=21)
target_compile_definitions(cmModLib++ INTERFACE MESON_MAGIC_FLAG=42)
target_link_libraries(cmModLib++ "${LIBRARIES}")
include_directories("${MY_PKG_INCLUDE_DIRS}")

include(GenerateExportHeader)
generate_export_header(cmModLib++)
