## Added `message` keyword arguments

The `message()` function gained two new keyword arguments to allow printing
messages in the same style as mesons own check messages.

The new kwargs are:

- `status`: A boolean indicating the status for the message, it will be
  printed as YES or NO.
- `extra_info`: A string with additional information to be printed after
  the status message in between parentheses. This could be a vesion number
  or other details on why the check was successful or not.


For example:

```
message('Found usable MinGW', status: true, extra_info: '10.0')
```

This would be printed as:

```
Found usable MinGW: YES (10.0)
```
