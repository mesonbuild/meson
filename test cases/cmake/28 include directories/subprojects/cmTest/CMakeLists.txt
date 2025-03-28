cmake_minimum_required(VERSION ${CMAKE_VERSION})

project(cmTest C)

add_library(cmTest src/cmTest.c)
target_include_directories(cmTest PUBLIC include)
