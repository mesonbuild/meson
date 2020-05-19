## Expose the thread model from dependency('threads')

Meson now exposes the threading model through the get_variable method.

```meson
dep_threads = dependency('threads', method : 'system')
model = dep_threads.get_variable(meson : 'model')
if model == 'win32'
  ...
elif model == 'posix'
  ...
else
  ...
endif
```

This is also exposed if CMAKE is used to find threads, but due to cmake's
implementation it is a bit different:

```meson
dep_threads = dependency('threads', method : 'cmake')
if dep_threads.get_variable(cmake : 'CMAKE_USE_WIN32_THREADS_INIT') == '1':
   # using windows threads
elif dep_threads.get_variable(cmake : 'CMAKE_USE_PTHREADS_INIT') == '1':
   # using pthreads.
endif
```
