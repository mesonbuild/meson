## Local wrap source and patch files

It is now possible to use the `patch_filename` and `source_filename` value in a
`.wrap` file without `*_url` to specify a local source / patch file. All local
files must be located in the `subprojects/packagefiles` directory. The `*_hash`
entries are optional with this setup.
