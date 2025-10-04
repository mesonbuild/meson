## Methods from compiler object now accept strings for include_directories

The various [[@compiler]] methods with a `include_directories` keyword argument
now accept stings or array of strings, in addition to [[@inc]] objects
generated from [[include_directories]] function, as it was already the case for
[[build_target]] family of functions.
