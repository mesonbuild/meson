## Improvements to Objective-C and Objective-C++

Meson does not assume anymore that gcc/g++ always support
Objective-C and Objective-C++, and instead checks that they
can actually do a basic compile.

Furthermore, Objective-C and Objective-C++ now support the
same language standards as C and C++ respectively.
