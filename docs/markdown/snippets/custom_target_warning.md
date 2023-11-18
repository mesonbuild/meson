## Inconsistency when passing a custom target to a command

Consider the following code that has 2 custom targets:

```meson
ct = custom_target(
    output: ['foo.txt', 'bar.txt'],
    command: ...,
)

custom_target(
    output: 'baz',
    command: ['script.py', ct],
)
```

The 2nd custom target will receive only `foo.txt` on its command line, instead of
expected `script.py foo.txt bar.txt`. Since this has always been the case and
no warning was printed, that behaviour had to be kept for backward compatibility,
but will now print a warning.

To avoid that warning, the above command should be `command: ['script.py', ct[0]]`.
If all outputs are desired on the command, it can be done as
`command: ['script.py', ct.to_list()]`.

This behaviour will be changed in the future to include all outputs on the command
line.

Note that this behaviour is inconsistent across different Meson functions.
For example, `meson.add_install_script('script.py', ct)` passes both `foo.txt`
and `bar.txt` to the command line.
