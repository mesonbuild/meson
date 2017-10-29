---
title: FAQ
...
# Meson Frequently Asked Questions

See also [How do I do X in Meson](howtox.md).

## Why is it called Meson?

When the name was originally chosen, there were two main limitations: there must not exist either a Debian package or a Sourceforge project of the given name. This ruled out tens of potential project names. At some point the name Gluon was considered. Gluons are elementary particles that hold protons and neutrons together, much like a build system's job is to take pieces of source code and a compiler and bind them to a complete whole.

Unfortunately this name was taken, too. Then the rest of subatomic particles were examined and Meson was found to be available.

## What is the correct way to use threads (such as pthreads)?

```meson
thread_dep = dependency('threads')
```

This will set up everything on your behalf. People coming from Autotools or CMake want to do this by looking for `libpthread.so` manually. Don't do that, it has tricky corner cases especially when cross compiling.

## How to use Meson on a host where it is not available in system packages?

Starting from version 0.29.0, Meson is available from the [Python Package Index](https://pypi.python.org/pypi/meson/), so installing it simply a matter of running this command:

```console
$ pip3 install <your options here> meson
```

If you don't have access to PyPI, that is not a problem either. Meson has been designed to be easily runnable from an extracted source tarball or even a git checkout. First you need to download Meson. Then use this command to set up you build instead of plain `meson`.

```console
$ /path/to/meson.py <options>
```

After this you don't have to care about invoking Meson any more. It remembers where it was originally invoked from and calls itself appropriately. As a user the only thing you need to do is to `cd` into your build directory and invoke `ninja`.

## Why can't I specify target files with a wildcard?

Instead of specifying files explicitly, people seem to want to do this:

```meson
executable('myprog', sources : '*.cpp') # This does NOT work!
```

Meson does not support this syntax and the reason for this is simple. This can not be made both reliable and fast. By reliable we mean that if the user adds a new source file to the subdirectory, Meson should detect that and make it part of the build automatically.

One of the main requirements of Meson is that it must be fast. This means that a no-op build in a  tree of 10 000 source files must take no more than a fraction of a second. This is only possible because Meson knows the exact list of files to check. If any target is specified as a wildcard glob, this is no longer possible. Meson would need to re-evaluate the glob every time and compare the list of files produced against the previous list. This means inspecting the entire source tree (because the glob pattern could be `src/\*/\*/\*/\*.cpp` or something like that). This is impossible to do efficiently.

The main backend of Meson is Ninja, which does not support wildcard matches either, and for the same reasons.

Because of this, all source files must be specified explicitly.

## But I really want to use wildcards!

If the tradeoff between reliability and convenience is acceptable to you, then Meson gives you all the tools necessary to do wildcard globbing. You are allowed to run arbitrary commands during configuration. First you need to write a script that locates the files to compile. Here's a simple shell script that writes all `.c` files in the current directory, one per line.


```bash
#!/bin/sh

for i in *.c; do
  echo $i
done
```

Then you need to run this script in your Meson file, convert the output into a string array and use the result in a target.

```meson
c = run_command('grabber.sh')
sources = c.stdout().strip().split('\n')
e = executable('prog', sources)
```

The script can be any executable, so it can be written in shell, Python, Lua, Perl or whatever you wish.

As mentioned above, the tradeoff is that just adding new files to the source directory does *not* add them to the build automatically. To add them you need to tell Meson to reinitialize itself. The simplest way is to touch the `meson.build` file in your source root. Then Meson will reconfigure itself next time the build command is run. Advanced users can even write a small background script that utilizes a filesystem event queue, such as [inotify](https://en.wikipedia.org/wiki/Inotify), to do this automatically.

## Should I use `subdir` or `subproject`?

The answer is almost always `subdir`. Subproject exists for a very specific use case: embedding external dependencies into your build process. As an example, suppose we are writing a game and wish to use SDL. Let us further suppose that SDL comes with a Meson build definition. Let us suppose even further that we don't want to use prebuilt binaries but want to compile SDL for ourselves.

In this case you would use `subproject`. The way to do it would be to grab the source code of SDL and put it inside your own source tree. Then you would do `sdl = subproject('sdl')`, which would cause Meson to build SDL as part of your build and would then allow you to link against it or do whatever else you may prefer.

For every other use you would use `subdir`. As an example, if you wanted to build a shared library in one dir and link tests against it in another dir, you would do something like this:

```meson
project('simple', 'c')
subdir('src')   # library is built here
subdir('tests') # test binaries would link against the library here
```

## Why is there not a Make backend?

Because Make is slow. This is not an implementation issue, Make simply can not be made fast. For further info we recommend you read [this post](http://neugierig.org/software/chromium/notes/2011/02/ninja.html) by Evan Martin, the author of Ninja. Makefiles also have a syntax that is very unpleasant to write which makes them a big maintenance burden.

The only reason why one would use Make instead of Ninja is working on a platform that does not have a Ninja port. Even in this case it is an order of magnitude less work to port Ninja than it is to write a Make backend for Meson.

Just use Ninja, you'll be happier that way. I guarantee it.

## Why is Meson not just a Python module so I could code my build setup in Python?

A related question to this is *Why is Meson's configuration language not Turing-complete?*

There are many good reasons for this, most of which are summarized on this web page: [Against The Use Of Programming Languages in Configuration Files](https://taint.org/2011/02/18/001527a.html).

In addition to those reasons, not exposing Python or any other "real" programming language makes it possible to port Meson's implementation to a different language. This might become necessary if, for example, Python turns out to be a performance bottleneck. This is an actual problem that has caused complications for GNU Autotools and SCons.

## How do I do the equivalent of Libtools export-symbol and export-regex?

Either by using [GCC symbol visibility](https://gcc.gnu.org/wiki/Visibility) or by writing a [linker script](https://ftp.gnu.org/old-gnu/Manuals/ld-2.9.1/html_mono/ld.html). This has the added benefit that your symbol definitions are in a standalone file instead of being buried inside your build definitions. An example can be found [here](https://github.com/jpakkane/meson/tree/master/test%20cases/linuxlike/3%20linker%20script).

## My project works fine on Linux and MinGW but fails with MSVC due to a missing .lib file

With GCC, all symbols on shared libraries are exported automatically unless you specify otherwise. With MSVC no symbols are exported by default. If your shared library exports no symbols, MSVC will silently not produce an import library file leading to failures. The solution is to add symbol visibility definitions [as specified in GCC wiki](https://gcc.gnu.org/wiki/Visibility).

## I added some compiler flags and now the build fails with weird errors. What is happening?

You probably did the equivalent to this:

```meson
executable('foobar', ...
           c_args : '-some_arg -other_arg')
```

Meson is *explicit*. In this particular case it will **not** automatically split your strings at whitespaces, instead it will take it as is and work extra hard to pass it to the compiler unchanged, including quoting it properly over shell invocations. This is mandatory to make e.g. files with spaces in them work flawlessly. To pass multiple command line arguments, you need to explicitly put them in an array like this:

```meson
executable('foobar', ...
           c_args : ['-some_arg', '-other_arg'])
```

## Why are changes to default project options ignored?

You probably had a project that looked something like this:

```meson
project('foobar', 'cpp')
```

This defaults to `c++11` on GCC compilers. Suppose you want to use `c++14` instead, so you change the definition to this:

```meson
project('foobar', 'cpp', default_options : ['cpp_std=c++14'])
```

But when you recompile, it still uses `c++11`. The reason for this is that default options are only looked at when you are setting up a build directory for the very first time. After that the setting is considered to have a value and thus the default value is ignored. To change an existing build dir to `c++14`, either reconfigure your build dir with `meson configure` or delete the build dir and recreate it from scratch.

## Does wrap download sources behind my back?

It does not. In order for Meson to download anything from the net while building, two conditions must be met.

First of all there needs to be a `.wrap` file with a download URL in the `subprojects` directory. If one does not exist, Meson will not download anything.

The second requirement is that there needs to be an explicit subproject invocation in your `meson.build` files. Either `subproject('foobar')` or `dependency('foobar', fallback : ['foobar', 'foo_dep'])`. If these declarations either are not in any build file or they are not called (due to e.g. `if/else`) then nothing is downloaded.

If this is not sufficient for you, starting from release 0.40.0 Meson has a option called `wrap-mode` which can be used to disable wrap downloads altogether with `--wrap-mode=nodownload`. You can also disable dependency fallbacks altogether with `--wrap-mode=nofallback`, which also implies the `nodownload` option.
