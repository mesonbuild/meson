## Test protocol for gtest

Due to the popularity of Gtest (google test) among C and C++ developers meson
now supports a special protocol for gtest. With this protocol meson injects
arguments to gtests to output JUnit, reads that JUnit, and adds the output to
the JUnit it generates.
