# Easier handling of supported compiler arguments

A common pattern for handling multiple desired compiler arguments, was to
test their presence and add them to an array one-by-one, e.g.:

    warning_flags_maybe = [
      '-Wsomething',
      '-Wanother-thing',
      '-Wno-the-other-thing',
    ]
    warning_flags = []
    foreach flag : warning_flags_maybe
      if cc.has_argument(flag)
        warning_flags += flag
      endif
    endforeach
    cc.add_project_argument(warning_flags)

A helper has been added for the foreach/has_argument pattern, so you can
now simply do:

    warning_flags = [ ... ]
    flags = cc.get_supported_flags(warning_flags)
