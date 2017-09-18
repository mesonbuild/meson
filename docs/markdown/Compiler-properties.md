# Compiler properties

Not all compilers and platforms are alike. Therefore Meson provides
the tools to detect properties of the system during configure time. To
get most of this information, you first need to extract the *compiler
object* from the main *meson* variable.

```meson
compiler = meson.get_compiler('c')
```

Here we extract the C compiler. We could also have given the argument
`cpp` to get the C++ compiler, `objc` to get the objective C compiler
and so on. The call is valid for all languages specified in the
*project* declaration. Trying to obtain some other compiler will lead
to an unrecoverable error.

## System information

This is a bit complex and more thoroughly explained on the page on
[cross compilation](Cross-compilation.md). But if you just want to
know the operating system your code will run on, issue this command:

```meson
host_machine.system()
```

Compiler id
==

The compiler object has a method called `get_id`, which returns a
lower case string describing the "family" of the compiler. See
[reference tables](Reference-tables.md) for a list of supported
compiler ids.

Does code compile?
==

Sometimes the only way to test the system is to try to compile some
sample code and see if it works. This is a two-phase operation. First
we define some code using the multiline string operator:

```meson
code = '''#include<stdio.h>
void func() { printf("Compile me.\n"); }
'''
```

Then we can run the test.

```meson
result = compiler.compiles(code, name : 'basic check')
```

The variable *result* will now contain either `true` or `false`
depending on whether the compilation succeeded or not. The keyword
argument `name` is optional. If it is specified, Meson will write the
result of the check to its log.

Does code compile and link?
==

Sometimes it is necessary to check whether a certain code fragment not
only compiles, but also links successfully, e.g. to check if a symbol
is actually present in a library. This can be done using the
'''.links()''' method on a compiler object like this:

```meson
code = '''#include<stdio.h>
void func() { printf("Compile me.\n"); }
'''
```

Then we can run the test.

```meson
result = compiler.links(code, args : '-lfoo', name : 'link check')
```

The variable *result* will now contain either `true` or `false`
depending on whether the compilation and linking succeeded or not. The
keyword argument `name` is optional. If it is specified, Meson will
write the result of the check to its log.


Compile and run test application
==

Here is how you would compile and run a small test application.

```meson
code = '''#include<stdio.h>
int main(int argc, char **argv) {
  printf("%s\n", "stdout");
  fprintf(stderr, "%s\n", "stderr");
  return 0;
}
'''
result = compiler.run(code, name : 'basic check')
```

The `result` variable encapsulates the state of the test, which can be
extracted with the following methods. The `name` keyword argument
works the same as with `compiles`.

| Method     | Return value                                                                                |
| ------     | ------------                                                                                |
| compiled   | `True` if compilation succeeded. If `false` then all other methods return undefined values. |
| returncode | The return code of the application as an integer                                            |
| stdout     | Program's standard out as text.                                                             |
| stderr     | Program's standard error as text.                                                           |

Here is an example usage:

```meson
if result.stdout().strip() == 'some_value'
  # do something
endif
```


Does a header exist?
==

Header files provided by different platforms vary quite a lot. Meson
has functionality to detect whether a given header file is available
on the system. The test is done by trying to compile a simple test
program that includes the specified header. The following snippet
describes how this feature can be used.

```meson
if compiler.has_header('sys/fstat.h')
  # header exists, do something
endif
```

Expression size
==

Often you need to determine the size of a particular element (such as
`int`, `wchar_t` or `char*`). Using the `compiler` variable mentioned
above, the check can be done like this.

```meson
wcharsize = compiler.sizeof('wchar_t', prefix : '#include<wchar.h>')
```

This will put the size of `wchar_t` as reported by sizeof into
variable `wcharsize`. The keyword argument `prefix` is optional. If
specified its contents is put at the top of the source file. This
argument is typically used for setting `#include` directives in
configuration files.

In older versions (<= 0.30) meson would error out if the size could
not be determined. Since version 0.31 it returns -1 if the size could
not be determined.

Does a function exist?
==

Just having a header doesn't say anything about its
contents. Sometimes you need to explicitly check if some function
exists. This is how we would check whether the function `somefunc`
exists in header `someheader.h`

```meson
if compiler.has_function('somefunc', prefix : '#include<someheader.h>')
  # function exists, do whatever is required.
endif
```

Does a structure contain a member?
==

Some platforms have different standard structures. Here's how one
would check if a struct called `mystruct` from header `myheader.h</hh>
contains a member called `some_member`.

```meson
if compiler.has_member('struct mystruct', 'some_member', prefix : '#include<myheader.h>')
  # member exists, do whatever is required
endif
```

Type alignment
==

Most platforms can't access some data types at any address. For
example it is common that a `char` can be at any address but a 32 bit
integer only at locations which are divisible by four. Determining the
alignment of data types is simple.

```meson
int_alignment = compiler.alignment('int') # Will most likely contain the value 4.
```

## Has argument

This method tests if the compiler supports a given command line
argument. This is implemented by compiling a small file with the given
argument.

```meson
has_special_flags = compiler.has_argument('-Wspecialthing')
```

*Note*: some compilers silently swallow command line arguments they do
not understand. Thus this test can not be made 100% reliable.
