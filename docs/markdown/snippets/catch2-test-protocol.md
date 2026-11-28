## New `catch2` test protocol

`test()` and `benchmark()` now accept `protocol: 'catch2'`. Meson invokes Catch2 3.x tests with the JUnit reporter and includes the results in `testlog.junit.xml`.
