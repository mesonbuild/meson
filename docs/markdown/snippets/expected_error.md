## Deprecate `should_fail` and rename it to `expected_fail`, also introduce `expected_exitcode`

In 1.11.0 `should_fail` has been renamed to `expected_error`.

Before 1.11.0, there was no way to positively test a command/binary returning error/non-zero exit code when the used protocol was set to exitcode, so `expected_exitcode` has been introduced to achieve this. Do note that if the exitcode does not match the expected value, GNU skip and exit codes are still valid and the test result may be skip or error.