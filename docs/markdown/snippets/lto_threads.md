## Knob to control LTO thread

Both the gnu linker and lld support using threads for speeding up LTO, meson
now provides a knob for this: `-Db_lto_threads`. Currently this is only
supported for clang and gcc. Any positive integer is supported, `0` means
`auto`. If the compiler or linker implements it's on `auto` we use that,
otherwise the number of threads on the machine is used.
