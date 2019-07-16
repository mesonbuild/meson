cmake_policy(VERSION 3.7)

if(CMAKE_VERSION VERSION_GREATER_EQUAL 3.12)
  find_package(Python COMPONENTS Interpreter)
else()
  find_package(PythonInterp)
endif()

if(Python_FOUND OR PYTHONINTERP_FOUND)
  set(SomethingLikePython_FOUND      ON)
  set(SomethingLikePython_EXECUTABLE ${Python_EXECUTABLE})

  if(NOT DEFINED Python_VERSION)
    set(Python_VERSION ${Python_VERSION_STRING})
  endif()
  if(NOT TARGET Python::Interpreter)
    add_executable(Python::Interpreter IMPORTED)
    set_target_properties(Python::Interpreter PROPERTIES
                          IMPORTED_LOCATION ${Python_EXECUTABLE}
                          VERSION ${Python_VERSION})
  endif()
else()
  set(SomethingLikePython_FOUND OFF)
endif()
