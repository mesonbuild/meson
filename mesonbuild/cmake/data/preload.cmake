if(MESON_PS_LOADED)
  return()
endif()

set(MESON_PS_LOADED ON)

# Dummy macros that have a special meaning in the meson code
macro(meson_ps_execute_delayed_calls)
endmacro()

macro(meson_ps_reload_vars)
endmacro()

# Helper macro to inspect the current CMake state
macro(meson_ps_inspect_vars)
  set(MESON_PS_CMAKE_CURRENT_BINARY_DIR "${CMAKE_CURRENT_BINARY_DIR}")
  set(MESON_PS_CMAKE_CURRENT_SOURCE_DIR "${CMAKE_CURRENT_SOURCE_DIR}")
  meson_ps_execute_delayed_calls()
endmacro()


# Override some system functions with custom code and forward the args
# to the original function
macro(add_custom_command)
  meson_ps_inspect_vars()
  _add_custom_command(${ARGV})
endmacro()

macro(add_custom_target)
  meson_ps_inspect_vars()
  _add_custom_target(${ARGV})
endmacro()

macro(set_property)
  meson_ps_inspect_vars()
  _set_property(${ARGV})
endmacro()

function(set_source_files_properties)
  set(FILES)
  set(I 0)
  set(PROPERTIES OFF)

  while(I LESS ARGC)
    if(NOT PROPERTIES)
      if("${ARGV${I}}" STREQUAL "PROPERTIES")
        set(PROPERTIES ON)
      else()
        list(APPEND FILES "${ARGV${I}}")
      endif()

      math(EXPR I "${I} + 1")
    else()
      set(ID_IDX ${I})
      math(EXPR PROP_IDX "${ID_IDX} + 1")

      set(ID   "${ARGV${ID_IDX}}")
      set(PROP "${ARGV${PROP_IDX}}")

      set_property(SOURCE ${FILES} PROPERTY "${ID}" "${PROP}")
      math(EXPR I "${I} + 2")
    endif()
  endwhile()
endfunction()

set(MESON_PS_DELAYED_CALLS add_custom_command;add_custom_target;set_property)
meson_ps_reload_vars()
