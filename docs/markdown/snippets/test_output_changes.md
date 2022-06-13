## Changes in the test output in the console

The way test details (when being verbose or printing details for a failed
test) get printed was updated. Most notable changes are:

* each line is prefixed with the relevant test number
* "headers" and indentation is used to group relevant lines together
* the style in which subtest results are listed changed

Specifying verbose option once will make test details be printed after a
test has completed. Specifying the verbose option twice will produce even
more output such as the raw output of a parsed test in test details.

The "live" output (when being verbose and using only one process) now
follows the (new) style of the normal verbose output more closely.

The "live" output is now automatically used when running only one test in
verbose mode.

The status line in quiet mode was simplified.

The main status line was updated to a multi line one. The status line is
also replaced with the quiet version if the size of the terminal is not at
least 80 characters wide and 24 rows tall.

Individual status lines longer than the width of the terminal are
shortened to fit on a single line.
