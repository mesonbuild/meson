## CMake custom targets accept arguments with backslashes

CMake subprojects can now configure `add_custom_target()` calls whose
arguments contain backslashes. Meson's preload wrapper previously expanded
those arguments a second time, which could reject valid command arguments
such as regular expression backreferences during configuration.
