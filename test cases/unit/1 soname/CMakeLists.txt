project(vertest C)
cmake_minimum_required(VERSION 3.5)

add_library(nover SHARED versioned.c)

add_library(verset SHARED versioned.c)
set_target_properties(verset PROPERTIES VERSION 4.5.6)

add_library(soverset SHARED versioned.c)
set_target_properties(soverset PROPERTIES SOVERSION 1.2.3)

add_library(bothset SHARED versioned.c)
set_target_properties(bothset PROPERTIES SOVERSION 1.2.3)
set_target_properties(bothset PROPERTIES VERSION 4.5.6)

add_library(settosame SHARED versioned.c)
set_target_properties(settosame PROPERTIES SOVERSION 7.8.9)
set_target_properties(settosame PROPERTIES VERSION 7.8.9)
