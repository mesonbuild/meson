cmake_minimum_required(VERSION 3.5)

project(subdir)

add_library(explicit_libs INTERFACE)

target_link_libraries(explicit_libs INTERFACE shell32.lib)
