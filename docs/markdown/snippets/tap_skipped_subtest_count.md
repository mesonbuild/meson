## TAP tests report how many subtests were skipped

The result line of a TAP test now reports how many of its subtests were
skipped, so environment-gated subtests no longer disappear silently from
a passing test:

    1/1 project:gated OK              0.02s   21 subtests passed, 5 skipped
