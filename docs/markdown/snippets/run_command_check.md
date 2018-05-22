## New 'check' keyword argument for the run_command function

If `check` is `true`, then the configuration will fail if the command returns a
non-zero exit status. The default value is `false` for compatibility reasons.
