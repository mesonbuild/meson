## Top-level statement handling in Swift libraries

The Swift compiler normally treats modules with a single source
file (and files named main.swift) to run top-level code at program
start. This emits a main symbol which is usually undesirable in a
library target. Meson now automatically passes the *-parse-as-library*
flag to the Swift compiler in case of single-file library targets to
disable this behavior unless the source file is called main.swift.
