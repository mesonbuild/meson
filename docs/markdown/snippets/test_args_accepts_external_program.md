## test() and benchmark() functions accept new types

`test` and `benchmark` now accept ExternalPrograms (as returned by
`find_program`) in the `args` list.  This can be useful where the test
executable is a wrapper which invokes another program given as an
argument.

```meson
test('some_test', find_program('sudo'), args : [ find_program('sh'), 'script.sh' ])
```
