## Unity file block size is configurable

Traditionally the unity files that Meson autogenerates contain all
source files that belong to a single target. This is the most
efficient setting for full builds but makes incremental builds slow.
This release adds a new option `unity_size` which specifies how many
source files should be put in each unity file.

The default value for block size is 4. This means that if you have a
target that has eight source files, Meson will generate two unity
files each of which includes four source files. The old behaviour can
be replicated by setting `unity_size` to a large value, such as 10000.
