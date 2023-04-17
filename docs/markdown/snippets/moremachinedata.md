## Machine objects get `kernel` and `subsystem` properties

Meson has traditionally provided a `system` property to detect the
system being run on. However this is not enough to reliably
differentiate between e.g. an iOS platform from a watchOS one. Two new
properties, namely `kernel` and `subsystem` have been added so these
setups can be reliably detected.

These new properties are not necessary in cross files for now, but if
they are not defined and a build file tries to access them, Meson will
exit with a hard error. It is expected that at some point in the
future defining the new properties will become mandatory.
