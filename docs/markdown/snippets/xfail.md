## Tests that should fail but did not are now errors

You can tag a test as needing to fail like this:

```meson
test('shoulfail', exe, should_fail: true)
```

If the test passes the problem is reported in the error logs but due
to a bug it was not reported in the test runner's exit code. Starting
from this release the unexpected passes are properly reported in the
test runner's exit code. This means that test runs that were passing
in earlier versions of Meson will report failures with the current
version. This is a good thing, though, since it reveals an error in
your test suite that has, until now, gone unnoticed.
