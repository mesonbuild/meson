# Access a variable directly from a subproject() invocation.

The keyword `variable` can be used to specify variable(s) whose value
should be returned directly from the subproject() invocation. This can be
used e.g. to directly access a dependency object from a subproject.

```
  somedep = subproject('someproj', variable : 'depvar')
  other_deps = subproject('otherproj', variable : ['depA', 'depB'])

  executable('foo', 'foo.c', dependencies : other_deps + [somedep])
```
