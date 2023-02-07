## Visual Studio VCXProj Filter Generation

Meson will now generate .vcxproj.filter files that mirror the directory
structure of the project when `--layout mirror` is used (default).

This makes working with large Meson projects that are organized by folder
in Visual Studio much easier.
