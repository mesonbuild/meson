## Local wrap source and patch files

It is now possible to use the `patch_filename` and `source_filename` value in a
`.wrap` file without `*_url` to specify a local source / patch file. All local
files must be located in the `subprojects/packagefiles` directory. The `*_hash`
entries are optional with this setup.

## Local wrap patch directory

Wrap files can now specify `patch_directory` instead of `patch_filename` in the
case overlay files are local. Every files in that directory, and subdirectories,
will be copied to the subproject directory. This can be used for example to add
`meson.build` files to a project not using Meson build system upstream.
The patch directory must be placed in `subprojects/packagefiles` directory.
