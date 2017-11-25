---
short-description: Syntax and structure of Meson files
...

# Syntax

The syntax of Meson's specification language has been kept as simple
as possible. It is *strongly typed* so no object is ever converted to
another under the covers. Variables have no visible type which makes
Meson *dynamically typed* (also known as *duck typed*).

The main building blocks of the language are *variables*, *numbers*,
*booleans*, *strings*, *arrays*, *function calls*, *method calls*, *if
statements* and *includes*.

Usually one Meson statement takes just one line. There is no way to
have multiple statements on one line as in e.g. *C*. Function and
method calls' argument lists can be split over multiple lines. Meson
will autodetect this case and do the right thing. In other cases you
can get multi-line statements by ending the line with a `\`. Apart
from line ending whitespace has no syntactic meaning.

Variables
--

Variables in Meson work just like in other high level programming
languages. A variable can contain a value of any type, such as an
integer or a string. Variables don't need to be predeclared, you can
just assign to them and they appear. Here's how you would assign
values to two different variables.

```meson
var1 = 'hello'
var2 = 102
```

One important difference in how variables work in Meson is that all
objects are immutable. This is different from, for example, how Python
works.

```meson
var1 = [1, 2, 3]
var2 = var1
var2 += [4]
# var2 is now [1, 2, 3, 4]
# var1 is still [1, 2, 3]
```

Numbers
--

Meson supports only integer numbers. They are declared simply by
writing them out. Basic arithmetic operations are supported.

```meson
x = 1 + 2
y = 3 * 4
d = 5 % 3 # Yields 2.
```

Strings can be converted to a number like this:

```meson
string_var = '42'
num = string_var.to_int()
```

Booleans
--

A boolean is either `true` or `false`.

```meson
truth = true
```

Strings
--

Strings in Meson are declared with single quotes. To enter a literal
single quote do it like this:

```meson
single quote = 'contains a \' character'
```

Similarly `\n` gets converted to a newline and `\\` to a single
backslash.

#### String concatenation

Strings can be concatenated to form a new string using the `+` symbol.

```meson
str1 = 'abc'
str2 = 'xyz'
combined = str1 + '_' + str2 # combined is now abc_xyz
```

#### Strings running over multiple lines

Strings running over multiple lines can be declared with three single
quotes, like this:

```meson
multiline_string = '''#include <foo.h>
int main (int argc, char ** argv) {
  return FOO_SUCCESS;
}'''
```

This can also be combined with the string formatting functionality
described below.

#### String formatting

Strings can be built using the string formatting functionality.

```meson
template = 'string: @0@, number: @1@, bool: @2@'
res = template.format('text', 1, true)
# res now has value 'string: text, number: 1, bool: true'
```

As can be seen, the formatting works by replacing placeholders of type
`@number@` with the corresponding argument.

#### String methods

Strings also support a number of other methods that return transformed
copies.

**.strip()**

```meson
# Similar to the Python str.strip(). Removes leading/ending spaces and newlines
define = ' -Dsomedefine '
stripped_define = define.strip()
# 'stripped_define' now has the value '-Dsomedefine'
```

**.to_upper()**, **.to_lower()**

```meson
target = 'x86_FreeBSD'
upper = target.to_upper() # t now has the value 'X86_FREEBSD'
lower = target.to_lower() # t now has the value 'x86_freebsd'
```

**.to_int()**

```meson
version = '1'
# Converts the string to an int and throws an error if it can't be
ver_int = version.to_int()
```

**.contains()**, **.startswith()**, **.endswith()**

```meson
target = 'x86_FreeBSD'
is_fbsd = target.to_lower().contains('freebsd')
# is_fbsd now has the boolean value 'true'
is_x86 = target.startswith('x86') # boolean value 'true'
is_bsd = target.to_lower().endswith('bsd') # boolean value 'true'
```

**.split()**, **.join()**

```meson
# Similar to the Python str.split()
components = 'a b   c d '.split()
# components now has the value ['a', 'b', 'c', 'd']
components = 'a b   c d '.split(' ')
# components now has the value ['a', 'b', '', '', 'c', 'd', '']

# Similar to the Python str.join()
output = ' '.join(['foo', 'bar'])
# Output value is 'foo bar'
pathsep = ':'
path = pathsep.join(['/usr/bin', '/bin', '/usr/local/bin'])
# path now has the value '/usr/bin:/bin:/usr/local/bin'

# For joining paths, you should use join_paths()
# This has the advantage of being cross-platform
path = join_paths(['/usr', 'local', 'bin'])
# path now has the value '/usr/local/bin'

# Example to set an API version for use in library(), install_header(), etc
project('project', 'c', version: '0.2.3')
version_array = meson.project_version().split('.')
# version_array now has the value ['0', '2', '3']
api_version = '.'.join([version_array[0], version_array[1]])
# api_version now has the value '0.2'

# We can do the same with .format() too:
api_version = '@0@.@1@'.format(version_array[0], version_array[1])
# api_version now (again) has the value '0.2'
```

**.underscorify()**

```meson
name = 'Meson Docs.txt#Reference-manual'
# Replaces all characters other than `a-zA-Z0-9` with `_` (underscore)
# Useful for substituting into #defines, filenames, etc.
underscored = name.underscorify()
# underscored now has the value 'Meson_Docs_txt_Reference_manual'
```

**.version_compare()**

```meson
version = '1.2.3'
# Compare version numbers semantically
is_new = version.version_compare('>=2.0')
# is_new now has the boolean value false
# Supports the following operators: '>', '<', '>=', '<=', '!=', '==', '='
```

Arrays
--

Arrays are delimited by brackets. An array can contain an arbitrary number of objects of any type.

```meson
my_array = [1, 2, 'string', some_obj]
```

Accessing elements of an array can be done via array indexing:

```meson
my_array = [1, 2, 'string', some_obj]
second_element = my_array[1]
last_element = my_array[-1]
```

You can add more items to an array like this:

```meson
my_array += ['foo', 3, 4, another_obj]
```

When adding a single item, you do not need to enclose it in an array:

```meson
my_array += ['something']
# This also works
my_array += 'else'
```

Note appending to an array will always create a new array object and
assign it to `my_array` instead of modifying the original since all
objects in Meson are immutable.

#### Array methods

The following methods are defined for all arrays:

 - `length`, the size of the array
 - `contains`, returns `true` if the array contains the object given as argument, `false` otherwise
 - `get`, returns the object at the given index, negative indices count from the back of the array, indexing out of bounds is a fatal error. Provided for backwards-compatibility, it is identical to array indexing.

Function calls
--

Meson provides a set of usable functions. The most common use case is
creating build objects.

```meson
executable('progname', 'prog.c')
```

Method calls
--

Objects can have methods, which are called with the dot operator. The
exact methods it provides depends on the object.

```meson
myobj = some_function()
myobj.do_something('now')
```

If statements
--

If statements work just like in other languages.

```meson
var1 = 1
var2 = 2
if var1 == var2 # Evaluates to false
  something_broke()
elif var3 == var2
  something_else_broke()
else
  everything_ok()
endif

opt = get_option('someoption')
if opt == 'foo'
  do_something()
endif
```

## Foreach statements

To do an operation on all elements of an array, use the `foreach`
command. As an example, here's how you would define two executables
with corresponding tests.

```meson
progs = [['prog1', ['prog1.c', 'foo.c']],
         ['prog2', ['prog2.c', 'bar.c']]]

foreach p : progs
  exe = executable(p[0], p[1])
  test(p[0], exe)
endforeach
```

Note that Meson variables are immutable. Trying to assign a new value
to `progs` inside a foreach loop will not affect foreach's control
flow.

Logical operations
--

Meson has the standard range of logical operations.

```meson
if a and b
  # do something
endif
if c or d
  # do something
endif
if not e
  # do something
endif
if not (f or g)
  # do something
endif
```

Logical operations work only on boolean values.

Comments
--

A comment starts with the `#` character and extends until the end of the line.

```meson
some_function() # This is a comment
some_other_function()
```

Ternary operator
--

The ternary operator works just like in other languages.

```meson
x = condition ? true_value : false_value
```

The only exception is that nested ternary operators are forbidden to
improve legibility. If your branching needs are more complex than this
you need to write an `if/else` construct.

Includes
--

Most source trees have multiple subdirectories to process. These can
be handled by Meson's `subdir` command. It changes to the given
subdirectory and executes the contents of `meson.build` in that
subdirectory. All state (variables etc) are passed to and from the
subdirectory. The effect is roughly the same as if the contents of the
subdirectory's Meson file would have been written where the include
command is.

```meson
test_data_dir = 'data'
subdir('tests')
```

User-defined functions and methods
--

Meson does not currently support user-defined functions or
methods. The addition of user-defined functions would make Meson
Turing-complete which would make it harder to reason about and more
difficult to integrate with tools like IDEs. More details about this
are [in the
FAQ](FAQ.md#why-is-meson-not-just-a-python-module-so-i-could-code-my-build-setup-in-python). If
because of this limitation you find yourself copying and pasting code
a lot you may be able to use a [`foreach` loop
instead](#foreach-statements).
