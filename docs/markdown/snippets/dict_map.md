## New `map()` method on dict

Dict now have a `map()` method that return a list of values from a given
list of keys.

It allows to keep objects in a dict, and to select needed objects from a list
of keys. For example:

```
dependencies = {
    'a': dependency('a'),
    'b': dependency('b'),
    'c': dependency('c'),
    ...
}

lib_dependencies = {
    'libA': ['a', 'b'],
    'libB': ['b', 'c'],
    ...
}

libA = library('A', dependencies: dependencies.map(lib_dependencies['libA']))
libB = library('B', dependencies: dependencies.map(lib_dependencies['libB']))
...

```
