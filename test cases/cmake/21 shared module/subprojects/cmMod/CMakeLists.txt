cmake_minimum_required(VERSION ${CMAKE_VERSION})

project(cmModule)

include_directories("${CMAKE_CURRENT_SOURCE_DIR}/module")

add_library(myMod MODULE "${CMAKE_CURRENT_SOURCE_DIR}/module/module.c")
