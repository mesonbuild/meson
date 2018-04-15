## Support for lcc compiler for e2k (Elbrus) architecture

In this version, a support for lcc compiler for Elbrus processors
based on [e2k microarchitecture](https://en.wikipedia.org/wiki/Elbrus_2000)
has been added.

Examples of such CPUs:
* [Elbrus-8S](https://en.wikipedia.org/wiki/Elbrus-8S);
* Elbrus-4S;
* [Elbrus-2S+](https://en.wikipedia.org/wiki/Elbrus-2S%2B).

Such compiler have a similar behavior as gcc (basic option compatibility),
but, in is not strictly compatible with gcc as of current version.

Major differences as of version 1.21.22:
* it does not support LTO and PCH;
* it suffers from the same dependency file creation error as icc;
* it has minor differences in output, especially version output;
* it differently reacts to lchmod() detection;
* some backend messages are produced in ru_RU.KOI8-R even if LANG=C;
* its preprocessor treats some characters differently.

So every noted difference is properly handled now in meson.