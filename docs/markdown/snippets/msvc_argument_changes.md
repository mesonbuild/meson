## MSVC/Clang-Cl Argument Changes/Cleanup

* "Disable Debug" (`/Od`) is no longer manually specified for optimization levels {`0`,`g`} (it is already the default for MSVC).
* "Run Time Checking" (`/RTC1`) removed from `debug` buildtype by default
* Clang-CL `debug` buildtype arguments now match MSVC arguments
* There is now no difference between `buildtype` flags and `debug` + `optimization` flags

The /Od flag has been removed, as it is already the default in the MSVC compilers, and conflicts with other user options.

/RTC1 conflicts with other RTC argument types as there are many different options, and has been removed by default.
Run Time Checking can be enabled by manually adding `/RTC1` or other RTC flags of your choice.

The `debug` buildtype for clang-cl added additional arguments compared to MSVC, which had more to do with optimization than debug. The arguments removed are `/Ob0`, `/Od`, `/RTC1`. (`/Zi` was also removed, but it is already added by default when debug is enabled.)

If these are important issues for you and would like builtin toggle options, 
please file an issue in the Meson bug tracker.