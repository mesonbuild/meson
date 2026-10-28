cmake_minimum_required(VERSION ${CMAKE_VERSION})

project(gen C)

add_executable(genprog genprog.c)
add_custom_command(OUTPUT generated.c COMMAND genprog generated.c)

add_library(genlib STATIC generated.c)
