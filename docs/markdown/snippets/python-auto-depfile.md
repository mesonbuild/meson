## Automatic python script dependencies

The `python` module `python_installation` has new `custom_target` and
`generator` methods that wraps the basic meson functions.

The command expects a Python script to be executed. The loaded Python
files during the execution will be automatically added by the module
runner as dependencies for the targets.
