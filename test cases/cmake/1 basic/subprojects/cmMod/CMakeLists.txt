cmake_minimum_required(VERSION 3.5)

project(cmMod)
set (CMAKE_CXX_STANDARD 14)

add_library(cmModLib SHARED cmMod.cpp)
