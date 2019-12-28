cmake_minimum_required(VERSION 3.5)

project(cmMod CXX)
set (CMAKE_CXX_STANDARD 14)

find_package(Threads)

add_library(cmModLib STATIC cmMod.cpp)
target_link_libraries(cmModLib PRIVATE Threads::Threads)
