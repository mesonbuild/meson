---
short-description: Common Code Generators Module
authors:
    - name: Dylan Baker
      email: dylan@pnwbakers.com
      years: [2024, 2025]
...

# Codegen Module

*(New in 1.10.0)*

This module provides wrappers around common code generators, such as flex/lex. This purpose of this is to make it easier and more pleasant to use *common* code generators in a mesonic way.

## Functions

### lex()

```meson
lex_gen = codegen.lex(implementations : ['flex', 'reflex'], flex_version : ['>= 2.6', '< 3'], reflex_version : '!= 1.4.2')
```

This function provides fine grained control over what implementation(s) and version(s) of lex are acceptable for a given project (These are set per-subproject). It returns a [new object](#lexgenerator), which can be used to generate code.

It accepts the following keyword arguments:

 - `implementations`: a string array of acceptable implementations to use. May include: `lex`, `flex`, `reflex`, or `win_flex`.
 - `lex_version`: a string array of version constraints to apply to the `lex` binary
 - `flex_version`: a string array of version constraints to apply to the `flex` binary
 - `reflex_version`: a string array of version constraints to apply to the `relex` binary
 - `win_flex_version`: a string array of version constraints to apply to the `win_flex` binary
 - `required`: A boolean or feature option
 - `disabler`: Return a disabler if not found
 - `native`: Is this generator for the host or build machine?

## Returned Objects

### LexGenerator

#### lex.implementation

```meson
lex = codegen.lex()
impl = lex.implementation()
```

Returns the string name of the lex implementation chosen. May be one of:

- lex
- flex
- reflex
- win_flex

#### lex.generate

```meson
lex = codegen.lex()
lex.generate('lexer.l')
```

This function wraps flex, lex, reflex (but not RE/flex), and win_flex (on Windows). When using win_flex it will automatically add the `--wincompat` argument.

This requires an input file, which may be a string, File, or generated source. It additionally takes the following options keyword arguments:

- `args`: An array of extra arguments to pass the lexer
- `plainname`: If set to true then `@PLAINNAME@` will be used as the source base, otherwise `@BASENAME@`.
- `source`: the name of the source output. If this is unset Meson will use `{base}.{ext}` with an extension of `cpp` if the input has an extension of `.ll`, or `c` otherwise, with base being determined by the `plainname` argument.
- `header`: The optional output name for a header file. If this is unset no header is added
- `table`: The optional output name for a table file. If this is unset no table will be generated

The outputs will be in the form `source [header] [table]`, which means those can be accessed by indexing the output of the `lex` call:

```meson
lex = codegen.lex()
l1 = lex.generate('lexer.l', header : '@BASENAME@.h', table : '@BASENAME@.tab.h')
headers = [l1[1], l1[2]]  # [header, table]

l2 = lex.generate('lexer.l', table : '@BASENAME@.tab.h')
table = l2[1]
```
