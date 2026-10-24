## Improved line splitting in `meson format`

`meson format` now decides where to split long lines in a single pass, and
splits more of the lines that are longer than `max_line_length`. Files that
were already formatted may be reformatted, so projects checking formatting
with `meson format --check-only` should run `meson format -i` once after
upgrading.

The new line splitting algorithm measured to be around 8% faster than the
previous algorithm.

The following changes affect the output:

- A line is now split even when only the text after a closing bracket makes
  it too long, for instance a comparison after a function call, or the
  trailing comma of an argument.

- Long chains of operators are split, one operand per line, wherever a line
  break is allowed (inside parentheses, function arguments, arrays and
  dicts). `and` / `or` are split first, then `+` / `-`, then `*` / `/` / `%`.

  ```meson
  custom_target(
      'linkcustom',
      output: 'libflob.a',
      command: [genprog, '-o', '@OUTPUT@', '--private-dir', '@PRIVATE_DIR@']
          + cc.cmd_array(),
  )
  ```

- Comments are no longer counted in the line length. A comment that makes
  its line longer than `max_line_length` is moved on its own line, above that
  line.

- With `sticky_parens = true`, a comment after the last operand of a
  multiline expression is moved after the closing parenthesis, even when code
  follows it.

- Fixed various indentation problems.
