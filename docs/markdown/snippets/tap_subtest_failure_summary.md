## Failing TAP tests list their subtests in the summary of failures

The summary of failures, printed with `--print-errorlogs` or `--verbose`,
now lists the failing and skipped subtests of each failing TAP test, both
on the console and in `testlog.txt`. On the console, `--verbose` lists all
subtests, including the passing ones:

    Summary of Failures:

    1/1 project:mixed FAIL            0.02s   2/3 subtests passed, 1 skipped
      ▶ sub-fail      FAIL
      ▶ sub-skip      SKIP
