## String escape character update

The strings (both single-quoted and triple-quoted) in meson has been taught the
same set of escape sequences as in Python. It is therefore now possible to use
arbitrary bytes in strings, like for example NUL (`\0`) and other ASCII control
characters. See the chapter about *Strings* in *Syntax* for more details.

Potential backwards compatibility issue: Any valid escape sequence according to
the new rules will be interpreted as an escape sequence instead of the literal
characters. Previously only single-quote strings supported escape sequences and
the supported sequences were `\'`, `\\` and `\n`.

The most likely breakage is usage of backslash-n in triple-quoted strings. It
is now written in the same way as in single-quoted strings: `\\n` instead of
`\n`. In general it is now recommended to escape any usage of backslash.
However, backslash-c (`\c`), for example, is still backslash-c because it isn't
a valid escape sequence.
