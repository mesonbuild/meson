## Coverage targets now respect tool config files

gcovr >= 4.2 supports `gcovr.cfg` in the project source root to configure how
coverage is generated. If Meson detects that gcovr will load this file, it no
longer excludes the `subprojects/` directory from coverage. It's a good default
for Meson to guess that projects want to ignore it, but not all projects prefer
that and it is assumed that if a gcovr.cfg exists then it will manually
include/exclude desired paths.

lcov supports `.lcovrc`, but only as a systemwide or user setting. This is
non-ideal for projects, so Meson will now detect one in the project source root
and, if present, manually tell lcov to use it.
