## New `python.dist_info_install_dir()` method

The `python` module's installation object gains a
`dist_info_install_dir(subdir)` method that returns an install directory
pointing at a subdirectory of the wheel's `.dist-info/` metadata
directory. Intended for files defined by Python packaging PEPs such as
PEP 770 SBOMs (`sboms`) and PEP 639 license files (`licenses`); Python
wheel build backends recognise the placeholder and route the file into
`<distname>-<version>.dist-info/<subdir>/` inside the wheel.
