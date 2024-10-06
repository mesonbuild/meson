cmake_minimum_required(VERSION ${CMAKE_VERSION})

project(cmTest LANGUAGES C OBJC)

include_directories(${CMAKE_CURRENT_BINARY_DIR})

add_library(cmTest STATIC cmTest.c cmTest.m)
target_compile_definitions(cmTest PUBLIC SOME_MAGIC_DEFINE=42)
