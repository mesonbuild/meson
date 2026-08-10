## `meson.can_run_host_binaries()` now accounts for Rosetta 2 on Apple Silicon

Previously, when cross-compiling for `x86_64` on an `aarch64` Mac,
[[meson.can_run_host_binaries]] (and the underlying `needs_exe_wrapper`
logic) always returned `false`, even though Rosetta 2 lets these Macs
execute `x86_64` binaries directly. Meson now detects whether Rosetta 2
is installed and, if so, reports that `x86_64` host binaries can run
natively without requiring an `exe_wrapper`.
