cmake_minimum_required(VERSION 3.5)

project(data)
set (CMAKE_CXX_STANDARD 14)

configure_file(data-dynamic.txt.in ${CMAKE_CURRENT_BINARY_DIR}/data-dynamic.txt @ONLY)
install(FILES data-static.txt ${CMAKE_CURRENT_BINARY_DIR}/data-dynamic.txt DESTINATION share)
