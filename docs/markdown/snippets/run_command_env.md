## `run_command` accepts `env` kwarg

You can pass [`environment`](Reference-manual.html#environment-object) object to [`run_command`](Reference-manual.html#run-command), just like to `test`:

```meson
env = environment()
env.set('FOO', 'bar')
run_command('command', 'arg1', 'arg2', env: env)
```
