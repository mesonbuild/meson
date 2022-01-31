## Changes in the test output in the console

The way test details (when being verbose or printing details for a failed
test) get printed was updated. Most notable changes are:

* each line is prefixed with the relevant test number
* "headers" and indentation is used to group relevant lines together
* the style in which subtest results are listed changed

Results of individual subtests are displayed only in verbose mode or when
printing details of a failed test. Specifying the verbose option twice
will now produce even more output including the unparsed full output of
the tests.

The "live" output (when being verbose and using only one process) now
follows the (new) style of the normal verbose output more closely.

The "live" output is now automatically used when running only one test in
verbose mode.

The status line in quiet mode was simplified.

The main status line was updated to a multi line one. The status line is
also replaced with the quiet version if the size of the terminal is not at
least 80 characters wide and 24 rows tall.
