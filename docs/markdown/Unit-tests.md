---
short-description: Meson's own unit-test system
...

# Unit tests

Meson comes with a fully functional unit test system. To use it simply build an executable and then use it in a test.

```meson
e = executable('prog', 'testprog.c')
test('name of test', e)
```

You can add as many tests as you want. They are run with the command `ninja test`.

Meson captures the output of all tests and writes it in the log file `meson-logs/testlog.txt`.

Test parameters
--

Some tests require the use of command line arguments or environment variables. These are simple to define.

```meson
test('command line test', exe, args : ['first', 'second'])
test('envvar test', exe2, env : ['key1=value1', 'key2=value2'])
```

Note how you need to specify multiple values as an array.

Coverage
--

If you enable coverage measurements by giving Meson the command line flag `-Db_coverage=true`, you can generate coverage reports. Meson will autodetect what coverage generator tools you have installed and will generate the corresponding targets. These targets are `coverage-xml` and `coverage-text` which are both provided by [Gcovr](http://gcovr.com) and `coverage-html`, which requires [Lcov](https://ltp.sourceforge.io/coverage/lcov.php) and [GenHTML](https://linux.die.net/man/1/genhtml).

The output of these commands is written to the log directory `meson-logs` in your build directory.

Parallelism
--

To reduce test times, Meson will by default run multiple unit tests in parallel. It is common to have some tests which can not be run in parallel because they require unique hold on some resource such as a file or a D-Bus name. You have to specify these tests with a keyword argument.

```meson
test('unique test', t, is_parallel : false)
```

Meson will then make sure that no other unit test is running at the same time. Non-parallel tests take longer to run so it is recommended that you write your unit tests to be parallel executable whenever possible.

By default Meson uses as many concurrent processes as there are cores on the test machine. You can override this with the environment variable `MESON_TESTTHREADS` like this.

```console
$ MESON_TESTTHREADS=5 ninja test
```

## Skipped tests

Sometimes a test can only determine at runtime that it can not be run. The GNU standard approach in this case is to exit the program with error code 77. Meson will detect this and report these tests as skipped rather than failed. This behavior was added in version 0.37.0.

## Testing tool

The goal of the meson test tool is to provide a simple way to run tests in a variety of different ways. The tool is designed to be run in the build directory.

The simplest thing to do is just to run all tests, which is equivalent to running `ninja test`.

```console
$ meson test
```

You can also run only a single test by giving its name:

```console
$ meson test testname
```

Sometimes you need to run the tests multiple times, which is done like this:

```console
$ meson test --repeat=10
```

Invoking tests via a helper executable such as Valgrind can be done with the `--wrap` argument

```console
$ meson test --wrap=valgrind testname
```

Arguments to the wrapper binary can be given like this:

```console
$ meson test --wrap='valgrind --tool=helgrind' testname
```

Meson also supports running the tests under GDB. Just doing this:

```console
$ meson test --gdb testname
```

Meson will launch `gdb` all set up to run the test. Just type `run` in the GDB command prompt to start the program.

The second use case is a test that segfaults only rarely. In this case you can invoke the following command:

```console
$ meson test --gdb --repeat=10000 testname
```

This runs the test up to 10 000 times under GDB automatically. If the program crashes, GDB will halt and the user can debug the application. Note that testing timeouts are disabled in this case so `meson test` will not kill `gdb` while the developer is still debugging it. The downside is that if the test binary freezes, the test runner will wait forever.

For further information see the command line help of Meson by running `meson test -h`.

**NOTE:** If `meson test` does not work for you, you likely have a old version of Meson. In that case you should call `mesontest` instead. If `mesontest` doesn't work either you have a very old version prior to 0.37.0 and should upgrade.
