# Cross compilation

Meson has full support for cross compilation. Since cross compiling is more complicated than native building,
let's first go over some nomenclature. The three most important definitions are traditionally called *build*, *host* and *target*. This is confusing because those terms are used for quite many different things. To simplify the issue, we are going to call these the *build machine*, *host machine* and *target machine*. Their definitions are the following

* *build machine* is the computer that is doing the actual compiling
* *host machine* is the machine on which the compiled binary will run
* *target machine* is the machine on which the compiled binary's output will run (this is only meaningful for programs such as compilers that, when run, produce object code for a different CPU than what the program is being run on)

The `tl/dr` summary is the following: if you are doing regular cross compilation, you only care about *build_machine* and *host_machine*. Just ignore *target_machine* altogether and you will be correct 99% of the time. If your needs are more complex or you are interested in the actual details, do read on.

This might be easier to understand through examples. Let's start with the regular, not cross-compiling case. In these cases all of these three machines are the same. Simple so far.

Let's next look at the most common cross-compilation setup. Let's suppose you are on a 64 bit OSX machine and you are cross compiling a binary that will run on a 32 bit ARM Linux board. In this case your *build machine* is 64 bit OSX and both your *host* and *target machines* are 32 bit ARM Linux. This should be quite understandable as well.

It gets a bit trickier when we think about how the cross compiler was generated. It was built and it runs on a specific platform but the output it generates is for a different platfom. In this case *build* and *host machines* are the same, but *target machine* is different.

The most complicated case is when you cross-compile a cross compiler. As an example you can, on a Linux machine, generate a cross compiler that runs on Windows but produces binaries on MIPS Linux. In this case *build machine* is x86 Linux, *host machine* is x86 Windows and *target machine* is MIPS Linux. This setup is known as the [Canadian Cross](https://en.wikipedia.org/wiki/Cross_compiler#Canadian_Cross). As a side note, be careful when reading cross compilation articles on Wikipedia or the net in general. It is very common for them to get build, host and target mixed up, even in consecutive sentences, which can leave you puzzled until you figure it out.

If you did not understand all of the details, don't worry. For most people it takes a while to wrap their head around these concepts. Don't panic, it might take a while to click, but you will get the hang of it eventually.

## Defining the environment

Meson requires you to write a cross build definition file. It defines various properties of the cross build environment. The cross file consists of different sections. The first one is the list of executables that we are going to use. A sample snippet might look like this:

```ini
[binaries]
c = '/usr/bin/i586-mingw32msvc-gcc'
cpp = '/usr/bin/i586-mingw32msvc-g++'
ar = '/usr/i586-mingw32msvc/bin/ar'
strip = '/usr/i586-mingw32msvc/bin/strip'
exe_wrapper = 'wine' # A command used to run generated executables.
```

The entries are pretty self explanatory but the last line is special. It defines a *wrapper command* that can be used to run executables for this host. In this case we can use Wine, which runs Windows applications on Linux. Other choices include running the application with qemu or a hardware simulator. If you have this kind of a wrapper, these lines are all you need to write. Meson will automatically use the given wrapper when it needs to run host binaries. This happens e.g. when running the project's test suite.

The next section lists properties of the cross compiler and thus of the target system. It looks like this:

```ini
[properties]
sizeof_int = 4
sizeof_wchar_t = 4
sizeof_void* = 4

alignment_char = 1
alignment_void* = 4
alignment_double = 4

has_function_printf = true

c_args = ['-DCROSS=1', '-DSOMETHING=3']
c_link_args = ['-some_link_arg']
```

In most cases you don't need the size and alignment settings, Meson will detect all these by compiling and running some sample programs. If your build requires some piece of data that is not listed here, Meson will stop and write an error message describing how to fix the issue. If you need extra compiler arguments to be used during cross compilation you can set them with `[langname]_args = [args]`. Just remember to specify the args as an array and not as a single string (i.e. not as `'-DCROSS=1 -DSOMETHING=3'`).

The last bit is the definition of host and target machines. Every cross build definition must have one or both of them. If it had neither, the build would not be a cross build but a native build. You do not need to define the build machine, as all necessary information about it is extracted automatically. The definitions for host and target machines look the same. Here is a sample for host machine.

```ini
[host_machine]
system = 'windows'
cpu_family = 'x86'
cpu = 'i686'
endian = 'little'
```

These values define the machines sufficiently for cross compilation purposes. The corresponding target definition would look the same but have `target_machine` in the header. These values are available in your Meson scripts. There are three predefined variables called, surprisingly, `build_machine`, `host_machine` and `target_machine`. Determining the operating system of your host machine is simply a matter of calling `host_machine.system()`.

There are two different values for the CPU. The first one is `cpu_family`. It is a general type of the CPU. Common values might include `x86`, `arm` or `x86_64`. The second value is `cpu` which is a more specific subtype for the CPU. Typical values for a `x86` CPU family might include `i386` or `i586` and for `arm` family `armv5` or `armv7hl`. Note that CPU type strings are very system dependent. You might get a different value if you check its value on the same machine but with different operating systems.

If you do not define your host machine, it is assumed to be the build machine. Similarly if you do not specify target machine, it is assumed to be the host machine.

## Starting a cross build


Once you have the cross file, starting a build is simple

```console
$ meson srcdir builddir --cross-file cross_file.txt
```

Once configuration is done, compilation is started by invoking Ninja in the usual way.

## Introspection and system checks

The main *meson* object provides two functions to determine cross compilation status.

```meson
meson.is_cross_build()  # returns true when cross compiling
meson.has_exe_wrapper() # returns true if an exe wrapper has been defined
```

Note that the latter gives undefined return value when doing a native build.

You can run system checks on both the system compiler or the cross compiler. You just have to specify which one to use.

```meson
build_compiler = meson.get_compiler('c', native : true)
host_compiler = meson.get_compiler('c', native : false)

build_int_size = build_compiler.sizeof('int')
host_int_size  = host_compiler.sizeof('int')
```

## Mixing host and build targets

Sometimes you need to build a tool which is used to generate source files. These are then compiled for the actual target. For this you would want to build some targets with the system's native compiler. This requires only one extra keyword argument.

```meson
native_exe = executable('mygen', 'mygen.c', native : true)
```

You can then take `native_exe` and use it as part of a generator rule or anything else you might want.

## Using a custom standard library

Sometimes in cross compilation you need to build your own standard library instead of using the one provided by the compiler. Meson has built-in support for switching standard libraries transparently. The invocation to use in your cross file is the following:

```ini
[properties]
c_stdlib = ['mylibc', 'mylibc_dep'] # Subproject name, dependency name
```

This specifies that C standard library is provided in the Meson subproject `mylibc` in internal dependency variable `mylibc_dep`. It is used on every cross built C target in the entire source tree (including subprojects) and the standard library is disabled. The build definitions of these targets do not need any modification.

## Changing cross file settings

Cross file settings are only read when the build directory is set up the first time. Any changes to them after the fact will be ignored. This is the same as regular compiles where you can't change the compiler once a build tree has been set up. If you need to edit your cross file, then you need to wipe your build tree and recreate it from scratch.

## Custom data

You can store arbitrary data in `properties` and access them from your Meson files. As an example if you cross file has this:

```ini
[properties]
somekey = 'somevalue'
```

then you can access that using the `meson` object like this:

```meson
myvar = meson.get_cross_property('somekey')
# myvar now has the value 'somevalue'
```
