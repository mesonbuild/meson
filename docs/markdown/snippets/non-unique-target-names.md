## Relaxing of target name requirements

In earlier versions of Meson you could only have one target of a given name for each type.
For example you could not have two executables named `foo`. This requirement is now
relaxed so that you can have multiple targets with the same name, as long as they are in
different subdirectories.

Note that projects that have multiple targets with the same name can not be built with
the `flat` layout or any backend that writes outputs in the same directory.
