## Warning if check kwarg of run_command is missing

The `check` kwarg of `run_command` currently defaults to `false`.
Because we want to change that, running
```meson
run_command('cmd')
```
now results in:
```text
WARNING: You should add the boolean check kwarg to the run_command call.
         It currently defaults to false,
         but it will default to true in future releases of meson.
         See also: https://github.com/mesonbuild/meson/issues/9300
```
