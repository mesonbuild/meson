## backend_startup_project can reference a target variable

If the value of `backend_startup_project` is not the name of a target, it
can be the name of a variable assigned to a target.

This allows referencing a target that has an unknown name at the point
default project options are specified:
```
project('startup_test', ['cpp'], default_options : ['backend_startup_project=b'])
my_suffix = '_some_suffix_based_off_environment'
a = executable('a' + my_suffix, 'main.cpp')
b = executable('b' + my_suffix, 'main.cpp')
```
