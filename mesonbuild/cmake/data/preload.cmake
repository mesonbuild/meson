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

set(MESON_PS_DELAYED_CALLS add_custom_command;add_custom_target)
meson_ps_reload_vars()
