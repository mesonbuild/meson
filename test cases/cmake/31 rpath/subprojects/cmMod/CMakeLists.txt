cmake_minimum_required(VERSION 3.5)

project(cmMod)
set (CMAKE_CXX_STANDARD 14)

add_library(cmModLibInternal SHARED cmMod_internal.cpp)
install(TARGETS cmModLibInternal LIBRARY DESTINATION private)

add_library(cmModLib++ SHARED cmMod.cpp)
target_link_libraries(cmModLib++ PUBLIC cmModLibInternal)
install(TARGETS cmModLib++ LIBRARY DESTINATION lib)
set_target_properties(cmModLib++ PROPERTIES INSTALL_RPATH "$ORIGIN/../private")
