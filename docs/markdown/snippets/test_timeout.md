## `test()` timeout and timeout_multiplier value <= 0

`test(..., timeout: 0)`, or negative value, used to abort the test immediately
but now instead allow infinite duration. Note that omitting the `timeout`
keyword argument still defaults to 30s timeout.

Likewise, `add_test_setup(..., timeout_multiplier: 0)`, or
`meson test --timeout-multiplier 0`, or negative value, disable tests timeout.

