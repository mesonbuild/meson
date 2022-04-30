# Getting Meson

## Installing Python

Meson requires requires Python >= 3.7, so you should install python
first. For ubuntu and other linux-based systems, it's easy to install python
via system package manager.

For Windows, you can use [scoop](https://scoop.sh/)
to install python. Open a powershell window, and execute
```
Set-ExecutionPolicy RemoteSigned -scope CurrentUser
iwr -useb get.scoop.sh | iex
scoop install python ninja
```

## Installing Meson

```
pip insall -U meson
```

## Dependencies

In the most common case, you will need the [Ninja executable] for
using the `ninja` backend, which is the default in Meson. This backend
can be used on all platforms and with all toolchains, including GCC,
Clang, Visual Studio, MinGW, ICC, ARMCC, etc.

You can use the version provided by your package manager if possible,
otherwise download the binary executable from the [Ninja project's
release page](https://github.com/ninja-build/ninja/releases).

If you will only use the Visual Studio backend (`--backend=vs`) to
generate Visual Studio solutions on Windows or the XCode backend
(`--backend=xcode`) to generate XCode projects on macOS, you do not
need Ninja.
