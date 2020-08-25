## Preliminary AIX support

AIX is now supported when compiling with gcc. A number of features are not
supported yet. For example, only gcc is supported (not xlC). Archives with both
32-bit and 64-bit dynamic libraries are not generated automatically. The rpath
includes both the build and install rpath, no attempt is made to change the
rpath at install time. Most advanced features (eg. link\_whole) are not
supported yet.
