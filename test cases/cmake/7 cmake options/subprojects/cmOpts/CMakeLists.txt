cmake_minimum_required(VERSION 3.7)

if(NOT "${SOME_CMAKE_VAR}" STREQUAL "something")
  message(FATAL_ERROR "Setting the CMake var failed")
endif()
