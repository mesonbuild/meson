cmake_minimum_required(VERSION ${CMAKE_MAJOR_VERSION}.${CMAKE_MINOR_VERSION}.${CMAKE_PATCH_VERSION} )

# Inspired by CMakeDetermineCompilerABI.cmake to set CMAKE_LIBRARY_ARCHITECTURE
if(CMAKE_LIBRARY_ARCHITECTURE_REGEX)
  if(NOT DEFINED CMAKE_LIBRARY_ARCHITECTURE)
    file(GLOB implicit_dirs RELATIVE /lib /lib/*-linux-gnu* )
    foreach(dir ${implicit_dirs})
      if("${dir}" MATCHES "${CMAKE_LIBRARY_ARCHITECTURE_REGEX}")
        set(CMAKE_LIBRARY_ARCHITECTURE "${dir}")
        break()
      endif()
    endforeach()
  endif()
endif()

set(PACKAGE_FOUND FALSE)

string(TOUPPER "${NAME}" NAME_A)
string(TOLOWER "${NAME}" NAME_B)
string(SUBSTRING "${NAME}" 0 1  NAME_FIRST_CHAR)
string(SUBSTRING "${NAME}" 1 -1 NAME_REMAINING)
string(TOUPPER "${NAME_FIRST_CHAR}" NAME_FIRST_CHAR_UPPER)
string(TOLOWER "${NAME_REMAINING}"  NAME_REMAINING_LOWER)

set(NAMES_TO_TRY "${NAME}" "${NAME_A}" "${NAME_B}" "${NAME_FIRST_CHAR_UPPER}${NAME_REMAINING}" "${NAME_FIRST_CHAR_UPPER}${NAME_REMAINING_LOWER}")

foreach(I IN LISTS NAMES_TO_TRY)
  find_package("${I}" QUIET)

  set(_packageName "${I}")
  string(TOUPPER "${_packageName}" PACKAGE_NAME)

  # Check if the package was NOT found, then continue with the next
  if(NOT ${_packageName}_FOUND AND NOT ${PACKAGE_NAME}_FOUND)
    continue()
  endif()

  # Package was found
  set(PACKAGE_FOUND TRUE)

  # Check the following variables:
  # FOO_VERSION
  # Foo_VERSION
  # FOO_VERSION_STRING
  # Foo_VERSION_STRING
  if(NOT DEFINED PACKAGE_VERSION)
    if(DEFINED ${_packageName}_VERSION)
      set(PACKAGE_VERSION "${${_packageName}_VERSION}")
    elseif(DEFINED ${PACKAGE_NAME}_VERSION)
      set(PACKAGE_VERSION "${${PACKAGE_NAME}_VERSION}")
    elseif(DEFINED ${_packageName}_VERSION_STRING)
      set(PACKAGE_VERSION "${${_packageName}_VERSION_STRING}")
    elseif(DEFINED ${PACKAGE_NAME}_VERSION_STRING)
      set(PACKAGE_VERSION "${${PACKAGE_NAME}_VERSION_STRING}")
    endif()
  endif()

  # Check the following variables:
  # FOO_LIBRARIES
  # Foo_LIBRARIES
  # FOO_LIBS
  # Foo_LIBS
  set(libs)
  if(DEFINED ${_packageName}_LIBRARIES)
    set(libs ${_packageName}_LIBRARIES)
  elseif(DEFINED ${PACKAGE_NAME}_LIBRARIES)
    set(libs ${PACKAGE_NAME}_LIBRARIES)
  elseif(DEFINED ${_packageName}_LIBS)
    set(libs ${_packageName}_LIBS)
  elseif(DEFINED ${PACKAGE_NAME}_LIBS)
    set(libs ${PACKAGE_NAME}_LIBS)
  endif()

  # Check the following variables:
  # FOO_INCLUDE_DIRS
  # Foo_INCLUDE_DIRS
  # FOO_INCLUDES
  # Foo_INCLUDES
  # FOO_INCLUDE_DIR
  # Foo_INCLUDE_DIR
  set(includes)
  if(DEFINED ${_packageName}_INCLUDE_DIRS)
    set(includes ${_packageName}_INCLUDE_DIRS)
  elseif(DEFINED ${PACKAGE_NAME}_INCLUDE_DIRS)
    set(includes ${PACKAGE_NAME}_INCLUDE_DIRS)
  elseif(DEFINED ${_packageName}_INCLUDES)
    set(includes ${_packageName}_INCLUDES)
  elseif(DEFINED ${PACKAGE_NAME}_INCLUDES)
    set(includes ${PACKAGE_NAME}_INCLUDES)
  elseif(DEFINED ${_packageName}_INCLUDE_DIR)
    set(includes ${_packageName}_INCLUDE_DIR)
  elseif(DEFINED ${PACKAGE_NAME}_INCLUDE_DIR)
    set(includes ${PACKAGE_NAME}_INCLUDE_DIR)
  endif()

  # Check the following variables:
  # FOO_DEFINITIONS
  # Foo_DEFINITIONS
  set(definitions)
  if(DEFINED ${_packageName}_DEFINITIONS)
    set(definitions ${_packageName}_DEFINITIONS)
  elseif(DEFINED ${PACKAGE_NAME}_DEFINITIONS)
    set(definitions ${PACKAGE_NAME}_DEFINITIONS)
  endif()

  set(PACKAGE_INCLUDE_DIRS "${${includes}}")
  set(PACKAGE_DEFINITIONS  "${${definitions}}")
  set(PACKAGE_LIBRARIES    "${${libs}}")

  break()
endforeach()
