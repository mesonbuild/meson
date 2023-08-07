# Features module

## Overview

Dealing with numerous CPU features through C and C++ compilers is a challenging task,
especially when aiming to support massive amount of CPU features for various architectures and multiple compilers
Additionally, supporting both baseline features and additional features dispatched at runtime presents another dilemma.

Another issue that may arise is simplifying the implementations of generic interfaces while keeping the dirty work laid
on the build system rather than using nested namespaces or recursive sources, relying on pragma or compiler targets attributes
on top of complicated precompiled macros or meta templates, which can make debugging and maintenance difficult.

While this module doesn't force you to follow a specific approach, it instead paves the way to count on a
practical multi-targets solution that can make managing CPU features easier and more reliable.

In a nutshell, this module helps you deliver the following concept:

```C
// Brings the headers files of enabled CPU features
#ifdef HAVE_SSE
    #include <xmmintrin.h>
#endif
#ifdef HAVE_SSE2
    #include <emmintrin.h>
#endif
#ifdef HAVE_SSE3
    #include <pmmintrin.h>
#endif
#ifdef HAVE_SSSE3
    #include <tmmintrin.h>
#endif
#ifdef HAVE_SSE41
    #include <smmintrin.h>
#endif
#ifdef HAVE_POPCNT
    #ifdef _MSC_VER
        #include <nmmintrin.h>
    #else
        #include <popcntintrin.h>
    #endif
#endif
#ifdef HAVE_AVX
    #include <immintrin.h>
#endif

#ifdef HAVE_NEON
    #include <arm_neon.h>
#endif

// MTARGETS_CURRENT defined as compiler argument via `features.multi_targets()`
#ifdef MTARGETS_CURRENT
    #define TARGET_SFX(X) X##_##MTARGETS_CURRENT
#else
    // baseline or when building source without this module.
    #define TARGET_SFX(X) X
#endif

void TARGET_SFX(my_kernal)(const float *src, float *dst)
{
#ifdef HAVE_AVX512F
    // defeintions for implied features alawys present
    // no matter the compiler is
    #ifndef HAVE_AVX2
        #error "Alawys defined"
    #endif
#elif defined(HAVE_AVX2) && defined(HAVE_FMA3)
    #ifndef HAVE_AVX
        #error "Alawys defined"
    #endif
#elif defined(HAVE_SSE41)
    #ifndef HAVE_SSSE3
        #error "Alawys defined"
    #endif
#elif defined(HAVE_SSE2)
    #ifndef HAVE_SSE2
        #error "Alawys defined"
    #endif
#elif defined(HAVE_ASIMDHP)
    #if !defined(HAVE_NEON) || !defined(HAVE_ASIMD)
        #error "Alawys defined"
    #endif
#elif defined(HAVE_ASIMD)
    #ifndef HAVE_NEON_VFPV4
        #error "Alawys defined"
    #endif
#elif defined(HAVE_NEON_F16)
    #ifndef HAVE_NEON
        #error "Alawys defined"
    #endif
#else
    // fallback to C scalar
#endif
}
```

From the above code we can deduce the following:
- The code is written on top features based definitions rather than counting clusters or
  features groups which gives the code more readability and flexibility.

- Avoid using compiler built-in defeintions no matters the enabled arguments allows you
  to easily manage the enabled/disabled features and to deal with any kind of compiler or features.
  Since compilers like MSVC for example doesn't provides defeintions for all CPU features.

- The code is not aware of how its going to be build it, that gives the code a great prodiblity to
  manage the generated objects which allow raising the baseline features at any time
  or reduce and increase the additional dispatched features without changing the code.

- Allow building a single source multiple of times simplifying the implementations
  of generic interfaces.


## Usage

To use this module, just do: **`features = import('features')`**. The
following functions will then be available as methods on the object
with the name `features`. You can, of course, replace the name `features`
with anything else.

### features.new()
```meson
features.new(string, int,
             implies: FeatureOject | FeatureObject[] = [],
             group: string | string[] = [],
             detect: string | {} | (string | {})[] = [],
             args: string | {} | (string | {})[] = [],
             test_code: string | File = '',
             extra_tests: {string: string | file} = {},
             disable: string = ''
             ) -> FeatureObject
```

This function plays a crucial role in the Features Module as it creates
a new `FeatureObject` instance that is essential for the functioning of
other methods within the module.

It takes two required positional arguments. The first one is the name of the feature,
and the second is the interest level of the feature, which is used by
the sort operation and priority of conflicting arguments.
The rest of the kwargs arguments are explained as follows:

* `implies` **FeatureOject | FeatureObject[] = []**: One or an array of features objects
  representing predecessor features.

* `group` **string | string[] = []**: Optional one or an array of extra features names
  to be added as extra definitions that can passed to source.

* `args` **string | {} | (string | {})[] = []**: Optional one or an array of compiler
  arguments that are required to be enabled for this feature.
  Each argument can be a string or a dictionary that holds four items that allow dealing
  with the conflicts of the arguments of implied features:
  - `val` **string**: string, the compiler argument.
  - `match` **string | empty**: regex to match the arguments of implied features
    that need to be filtered or erased.
  - `mfilter` **string | empty**: regex to find certain strings from the matched arguments
    to be combined with `val`. If the value of `mfilter` is empty or undefined,
    any matches triggered by the value of `match` will not be combined with `val`.
  - `mjoin` **string | empty**:  a separator used to join all the filtered arguments.
    If it's empty or undefined, the filtered arguments will be joined without a separator.

* `detect` **string | {} | (string | {})[] = []**: Optional one or an array of features names
  that required to be detect on runtime. If no features sepecfied then the values of `group`
  will be used if its provides otherwise the name of the feature will be used instead.
  Similar to `args`, each feature name can be a string or a dictionary that holds four items
  that allow dealing with the conflicts of the of implied features names.
  See `features.multi_targets()` or `features.test()` for more clearfications.

* `test_code` **string | File = ''**: Optional C/C++ code or the path to the source
  that needs to be tested against the compiler to consider this feature is supported.

* `extra_tests` **{string: string | file} = {}**: Optional dictionary holds extra tests where
  the key represents the test name, which is also added as a compiler definition if the test succeeded,
  and the value is C/C++ code or the path to the source that needs to be tested against the compiler.

* `disable` **string = ''**: Optional string to consider this feature disabled.

Returns a new instance of `FeatureObject`.

Example:

```Meson
cpu = host_machine.cpu_family()
features = import('features')

ASIMD = features.new(
  'ASIMD', 1, group: ['NEON', 'NEON_VFPV4', 'NEON_VFPV4'],
  args: cpu == 'aarch64' ? '' : [
    '-mfpu=neon-fp-armv8',
    '-march=armv8-a+simd'
  ],
  disable: cpu in ['arm', 'aarch64'] ? '' : 'Not supported by ' + cpu
)
# ARMv8.2 half-precision & vector arithm
ASIMDHP = features.new(
  'ASIMDHP', 2, implies: ASIMD,
  args: {
    'val': '-march=armv8.2-a+fp16',
    # search for any argument starts with `-match=`
    'match': '-march=',
    # gets any string starts with `+` and apended to the value of `val`
    'mfilter': '\+.*'
  }
)
## ARMv8.2 dot product
ASIMDDP = features.new(
  'ASIMDDP', 3, implies: ASIMD,
  args: {'val': '-march=armv8.2-a+dotprod', 'match': '-march=.*', 'mfilter': '\+.*'}
)
## ARMv8.2 Single & half-precision Multiply
ASIMDFHM = features.new(
  'ASIMDFHM', 4, implies: ASIMDHP,
  args: {'val': '-march=armv8.2-a+fp16fml', 'match': '-march=.*', 'mfilter': '\+.*'}
)
```

### features.test()
```meson
features.test(FeatureObject...,
              anyfet: bool = false,
              force_args: string | string[] | empty = empty,
              compiler: Compiler | empty = empty,
              cached: bool = true,
             ) -> {}
```

Test a one or set of features against the compiler and returns a dictionary
contains all required information that needed for building a source that
requires these features.

### features.multi_targets()
```meson
features.multi_targets(string, (
                        str | File | CustomTarget | CustomTargetIndex |
                        GeneratedList | StructuredSources | ExtractedObjects |
                        BuildTarget
                       )...,
                       dispatch: (FeatureObject | FeatureObject[])[] = [],
                       baseline: empty | FeatureObject[] = empty,
                       prefix: string = '',
                       compiler: empty | compiler = empty,
                       cached: bool = True
                       )  [{}[], StaticLibrary[]]
```


### features.sort()
```meson
features.sort(FeatureObject..., reverse: bool = false) : FeatureObject[]
```

### features.implicit()
```meson
features.implicit(FeatureObject...) : FeatureObject[]
```

### features.implicit_c()
```meson
features.implicit_c(FeatureObject...) : FeatureObject[]
```

