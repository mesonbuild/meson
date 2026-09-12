cmake_minimum_required(VERSION ${CMAKE_VERSION})

project(cmTest C)

add_library(cmTestLib_objs OBJECT "x.c")
set_target_properties(cmTestLib_objs PROPERTIES POSITION_INDEPENDENT_CODE TRUE)

add_library(cmTestLib STATIC $<TARGET_OBJECTS:cmTestLib_objs>)
set_target_properties(cmTestLib PROPERTIES POSITION_INDEPENDENT_CODE TRUE)
