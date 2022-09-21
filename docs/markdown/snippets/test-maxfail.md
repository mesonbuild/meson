## Option to allow meson test to fail fast after the first failing testcase

`meson test --maxfail=1` will now cause all pending or in-progress tests to be
canceled or interrupted after 1 test is marked as failing. This can be used for
example to quit a CI run and avoid burning additional time as soon as it is
known that the overall return status will be failing.
