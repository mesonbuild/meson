## `invert_result` option added to test()

This is very similar to "should_fail", but does not change the test results to
"Expected Fail" / "Unexpected Pass".

"Expected Fail" and "Unexpected Pass" are useful when they communicate to
developers that additional work needs to be done, e.g. as part of Test
Driven Development or to demonstrate problems with some edge cases that need
to be addressed in the future.

In other cases, a non-zero status code is actually the whole test, e.g. a
program under test that is expected to exit with a non-zero status code when
given invalid arguments or a bad configuration file. This is the expected
behavior and hence should be reported as "Pass", not "Expected Fail".

"invert_result" and "should_fail" can be combined to produce "Unexpected Pass"
for non-zero status codes and "Expected Fail" for zero status codes.

```meson
test(
    'fail if config file is missing',
    executable(...),
    args: [ '--config', '/path/does/not/exist' ],
    invert_result: true)
```
