## Deprecate `should_fail` and rename it to `expected_fail`, also introduce `expected_exitcode`

In 1.9.0 `should_fail` has been renamed to `expected_error`. 

Before 1.9.0, there was no way to positively test a command/binary returning error/non-zero exit code when the used protocol was set to exitcode, so `expected_exitcode` has been introduced to achieve this.