## Support for reading options from meson.options

Support has been added for reading options from `meson.options` instead of
`meson_options.txt`. These are equivalent, but not using the `.txt` extension
for a build file has a few advantages, chief among them many tools and text
editors expect a file with the `.txt` extension to be plain text files, not
build scripts.
