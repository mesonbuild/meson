## New end_messages method

The new `end_messages` function allows you to create status messages
that will be printed at the end of the Meson run rather than
immediately. For example the following setup:

```meson
end_message('A short name:', 'value #1')
end_message('A bit longer name:', 'value #2')
```

Will cause the following text to be printed as the last thing just
before Meson exits.

```
Main project

A short name:       value #1
A bit longer name:  value #2
```
