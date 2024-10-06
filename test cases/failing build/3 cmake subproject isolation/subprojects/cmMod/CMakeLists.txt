cmake_minimum_required(VERSION ${CMAKE_VERSION})

project(cmMod)
set (CMAKE_CXX_STANDARD 14)

include_directories(${CMAKE_CURRENT_BINARY_DIR} ${MESON_INC_DIR})

add_library(cmModLib++ SHARED cmMod.cpp)
include(GenerateExportHeader)
generate_export_header(cmModLib++)
