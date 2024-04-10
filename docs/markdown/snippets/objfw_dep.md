## A new dependency for ObjFW is now supported

For example, you can create a simple application written using ObjFW like this:

```meson
project('SimpleApp', 'objc')

objfw_dep = dependency('objfw', version: '>= 1.0')

executable('SimpleApp', 'SimpleApp.m',
  dependencies: [objfw_dep])
```

Modules are also supported. A test case using ObjFWTest can be created like
this:

```meson
project('Tests', 'objc')

objfwtest_dep = dependency('objfw', version: '>= 1.1', modules: ['ObjFWTest'])

executable('Tests', ['FooTest.m', 'BarTest.m'],
  dependencies: [objfwtest_dep])
```
