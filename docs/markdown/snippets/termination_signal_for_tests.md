## Changed the signal used to terminate a test process (group)

A test process (group) is now terminated via SIGTERM instead of SIGKILL
allowing the signal to be handled. However, it is now the responsibility of
the custom signal handler (if any) to ensure that any process spawned by the
top-level test processes is correctly killed.
