## Support of indexed `@PLAINNAME@` and `@BASENAME@`

In `custom_target()` and `configure_file()` with multiple inputs,
it is now possible to specify index for `@PLAINNAME@` and `@BASENAME@`
macros in `output`:
```
custom_target('target_name',
  output: '@PLAINNAME0@.dl',
  input: [dep1, dep2],
  command: cmd)
```
