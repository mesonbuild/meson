## Add `filter` and `filter_out` methods for lists

Two new functions are added for filtering elements from a list based on a regex. `filter` returns a new list containing only elements
matching the given regex, while `filter_out` returns a new list containing only elements that do not match the given regex.

Both methods have a single kwarg `pattern` specifying the regex to apply to each element of the target list. The
list is given as positional arguments, operating on either the entire list of positional args or the first positional arg if it is a list.
