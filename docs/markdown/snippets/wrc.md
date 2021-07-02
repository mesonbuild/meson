## Support for the Wine Resource Compiler

Users can now choose `wrc` as the `windres` binary in their cross files and
`windows.compile_resources` will handle it correctly. Together with `winegcc`
patches in Wine 6.12 this enables basic support for compiling projects as a
winelib by specifying `winegcc`/`wineg++` as the compiler and `wrc` as the
resource compiler in a cross file.
