cmake_minimum_required(VERSION 3.5)

project(cmMod)
set (CMAKE_CXX_STANDARD 14)
set (CMAKE_CXX_STANDARD_REQUIRED ON)

include_directories(${CMAKE_CURRENT_BINARY_DIR})
add_definitions("-DDO_NOTHING_JUST_A_FLAG=1")

add_executable(gen main.cpp)
add_executable(mycpy cp.cpp)

# cpyBase
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

# cpyNext (out of order is on purpose)
# -- first copy round
add_custom_command(
  OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/s1_a_hpp/file.txt"
  COMMAND mycpy "${CMAKE_CURRENT_SOURCE_DIR}/cpyNext.hpp.am" file.txt
  DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/cpyNext.hpp.am"
  WORKING_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/s1_a_hpp"
)

add_custom_command(
  OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/s1_b_cpp/file.txt"
  COMMAND mycpy "${CMAKE_CURRENT_SOURCE_DIR}/cpyNext.cpp.am" file.txt
  DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/cpyNext.cpp.am"
  WORKING_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/s1_b_cpp"
)

# -- final cpy round
add_custom_command(
  OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/cpyNext.hpp"
  COMMAND mycpy "${CMAKE_CURRENT_BINARY_DIR}/s2_b_hpp/file.txt" cpyNext.hpp
  DEPENDS "${CMAKE_CURRENT_BINARY_DIR}/s2_b_hpp/file.txt"
  WORKING_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}"
)

add_custom_command(
  OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/cpyNext.cpp"
  COMMAND mycpy "${CMAKE_CURRENT_BINARY_DIR}/s2_a_cpp/file.txt" cpyNext.cpp
  DEPENDS "${CMAKE_CURRENT_BINARY_DIR}/s2_a_cpp/file.txt"
  WORKING_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}"
)

# -- second copy round
add_custom_command(
  OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/s2_b_hpp/file.txt"
  COMMAND mycpy "${CMAKE_CURRENT_BINARY_DIR}/s1_a_hpp/file.txt" file.txt
  DEPENDS "${CMAKE_CURRENT_BINARY_DIR}/s1_a_hpp/file.txt"
  WORKING_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/s2_b_hpp"
)

add_custom_command(
  OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/s2_a_cpp/file.txt"
  COMMAND mycpy "${CMAKE_CURRENT_BINARY_DIR}/s1_b_cpp/file.txt" file.txt
  DEPENDS "${CMAKE_CURRENT_BINARY_DIR}/s1_b_cpp/file.txt"
  WORKING_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/s2_a_cpp"
)

add_library(cmModLib SHARED cmMod.cpp genTest.cpp cpyBase.cpp cpyBase.hpp cpyNext.cpp cpyNext.hpp)
include(GenerateExportHeader)
generate_export_header(cmModLib)

set(ARGS_TEST arg1)
set(ARGS_TEST ${ARGS_TEST} arg2)

add_executable(macro_name macro_name.cpp)
add_executable(args_test args_test.cpp)
add_custom_target(args_test_cmd
  COMMAND args_test ARGS ${ARGS_TEST}
)
add_custom_target(macro_name_cmd COMMAND macro_name)

add_dependencies(cmModLib args_test_cmd)
add_dependencies(args_test_cmd macro_name_cmd)
