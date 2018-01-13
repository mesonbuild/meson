## Removed two deprecated features

The standalone `find_library` function has been a no-op for a long
time. Starting with this version it becomes a hard error.

There used to be a keywordless version of `run_target` which looked
like this:

    run_target('targetname', 'command', 'arg1', 'arg2')

This is now an error. The correct format for this is now:

    run_target('targetname',
      command : ['command', 'arg1', 'arg2'])
