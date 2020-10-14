## Search for dependencies in the installation prefix

Meson has now the `--default-dependency-sources=both` setting, that tells pkg-config and cmake
to search for dependencies both in the system and in the installation prefix. By
default the behaviour is to search only in the system (`--default-dependency-sources=system`).
