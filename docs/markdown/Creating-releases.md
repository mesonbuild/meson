---
short-description: Creating releases
...

# Creating releases

In addition to development, almost all projects provide periodical
source releases. These are standalone packages (usually either in tar
or zip format) of the source code. They do not contain any revision
control metadata, only the source code.

Meson provides a simple way of generating these. It consists of a
single command:

    ninja dist

This creates a file called `projectname-version.tar.xz` in the build
tree subdirectory `meson-dist`. This archive contains the full
contents of the latest commit in revision control including all the
submodules. All revision control metadata is removed. Meson then takes
this archive and tests that it works by doing a full compile + test +
install cycle. If all these pass, Meson will then create a SHA-256
checksum file next to the archive.

**Note**: Meson behaviour is different from Autotools. The Autotools
"dist" target packages up the current source tree. Meson packages
the latest revision control commit. The reason for this is that it
prevents developers from doing accidental releases where the
distributed archive does not match any commit in revision control
(especially the one tagged for the release).
