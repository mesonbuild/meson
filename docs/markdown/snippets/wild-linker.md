## Wild linker is now supported on Linux

When `CC_LD` environment variables is set to `wild`, Meson will configure GCC 16+ or Clang
to use Wild as the linker on Linux. You should expect to see line like this in the output:
`C linker for the host machine: cc ld.wild 0.10.0` confirming that Wild was picked up.
