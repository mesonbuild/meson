## New `sourceset` module

A new module, `sourceset`, was added to help building many binaries
from the same source files.  Source sets associate source files and
dependencies to keys in a `configuration_data` object or a dictionary;
they then take multiple `configuration_data` objects or dictionaries,
and compute the set of source files and dependencies for each of those
configurations.
