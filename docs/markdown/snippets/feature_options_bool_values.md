## Feature options now accept true and false

It's currently pretty painful to convert a boolean option to a feature option,
because command lines that have previously worked (and are probably embedded
into scripts) will just stop working. This is really an artificial limitation.

Meson will now accept true and false on the command line for feature options,
which map to enabled and disabled respectively.
