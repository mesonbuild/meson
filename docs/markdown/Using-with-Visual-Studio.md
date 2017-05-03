---
short-description: How to use meson in Visual Studio
...

# Using with Visual Studio

In order to generate Visual Studio projects, Meson needs to know the settings of your installed version of Visual Studio. The only way to get this information is to run Meson under the Visual Studio Command Prompt. The steps to set it up are as follows:

1. Click on start menu and select "Visual Studio 2015 Command Prompt"
1. cd into your source directory
1. mkdir builddir
1. python3 path/to/meson.py builddir --backend vs2015

If you wish to use the Ninja backend instead of vs2015, pass `--backend ninja`. At the time of writing the Ninja backend is more mature than the VS backend so you might want to use it for serious work.

This assumes Python3 is in your `PATH`, which is highly recommended.
