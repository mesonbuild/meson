## String escape character sequence update

Single-quoted strings in meson have been taught the same set of escape
sequences as in Python. It is therefore now possible to use arbitrary bytes in
strings, like for example `NUL` (`\0`) and other ASCII control characters. See
the chapter about [*Strings* in *Syntax*](Syntax.md#strings) for more
details.

Potential backwards compatibility issue: Any valid escape sequence according to
the new rules will be interpreted as an escape sequence instead of the literal
characters. Previously only the following escape sequences were supported in
single-quote strings: `\'`, `\\` and `\n`.

Note that the behaviour of triple-quoted (multiline) strings has not changed.
They behave like raw strings and do not support any escape sequences.
