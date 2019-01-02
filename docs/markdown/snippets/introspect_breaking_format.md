## Changed the JSON format of the introspection

All paths used in the meson introspection JSON format are now absolute. This
affects the `filename` key in the targets introspection and the output of
`--target-files` and `--buildsystem-files`.

Furthermore, the `filename` and `install_filename` keys in the targets
introspection are now lists of strings with identical length.
