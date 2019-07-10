cmake_minimum_required(VERSION 3.5)

project(cmMod)
set (CMAKE_CXX_STANDARD 14)

include_directories(${CMAKE_CURRENT_BINARY_DIR})
add_definitions("-DDO_NOTHING_JUST_A_FLAG=1")

add_executable(gen main.cpp)
add_executable(mycpy cp.cpp)

add_custom_command(
  OUTPUT  "${CMAKE_CURRENT_BINARY_DIR}/genTest.cpp" "${CMAKE_CURRENT_BINARY_DIR}/genTest.hpp"
  COMMAND gen ARGS genTest
)

add_custom_command(
  OUTPUT cpyBase.cpp
  COMMAND mycpy "${CMAKE_CURRENT_SOURCE_DIR}/cpyBase.cpp.am" cpyBase.cpp.in
  COMMAND mycpy cpyBase.cpp.in                               cpyBase.cpp.something
  COMMAND mycpy cpyBase.cpp.something                        cpyBase.cpp.IAmRunningOutOfIdeas
  COMMAND mycpy cpyBase.cpp.IAmRunningOutOfIdeas             cpyBase.cpp
  DEPENDS cpyBase.cpp.am gen
)

add_custom_command(
  OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/cpyBase.hpp.in"
  COMMAND mycpy "${CMAKE_CURRENT_SOURCE_DIR}/cpyBase.hpp.am" cpyBase.hpp.in
  DEPENDS cpyBase.hpp.am
)

add_custom_command(
  OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/cpyBase.hpp.something"
  COMMAND mycpy cpyBase.hpp.in                               cpyBase.hpp.something
  DEPENDS "${CMAKE_CURRENT_BINARY_DIR}/cpyBase.hpp.in"
)

add_custom_command(
  OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/cpyBase.hpp"
  COMMAND mycpy cpyBase.hpp.something                        cpyBase.hpp
  DEPENDS "${CMAKE_CURRENT_BINARY_DIR}/cpyBase.hpp.something"
)

add_library(cmModLib SHARED cmMod.cpp genTest.cpp cpyBase.cpp cpyBase.hpp)
include(GenerateExportHeader)
generate_export_header(cmModLib)
