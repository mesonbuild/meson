project('very long command lines', 'c')

# Get the current system's commandline length limit.
if build_machine.system() == 'windows'
  # Various limits on windows:
  # cmd.exe: 8kb
  # CreateProcess: 32kb
  MAX_ARG_STRLEN = 32767
elif build_machine.system() == 'cygwin'
  # cygwin-to-win32: see above
  # cygwin-to-cygwin: no limit?
  # Not sure it's worth testing the cygwin-to-win32 case too hard, it's slow.
  MAX_ARG_STRLEN = 8192
else
  # os.sysconf('SC_ARG_MAX') is useless since ninja uses posix_spawn,
  # which passes whole line as a single argument to sh.
  # Limit for a single argument from Linux 2.6.23 and on is 32 pages.
  # See https://www.in-ulm.de/~mascheck/various/argmax
  # BSD seems similar.
  MAX_ARG_STRLEN = 131072
endif
# Now exceed that limit, but not so far that the test takes too long.
name = 'ALongFilenameMuchLongerThanIsNormallySeenAndReallyHardToReadThroughToTheEndAMooseOnceBitMySisterSheNowWorksAtLLamaFreshFarmsThisHasToBeSoLongThatWeExceed128KBWithoutCompilingTooManyFiles'
namelen = 187
nfiles = 50 + MAX_ARG_STRLEN / namelen
message('Expected link commandline length is approximately ' + '@0@'.format((nfiles * (namelen+28))))

seq = run_command('seq.py', '1', '@0@'.format(nfiles)).stdout().strip().split('\n')

sources = []
codegen = find_program('codegen.py')

foreach i : seq
  sources += custom_target('codegen' + i,
                           command: [codegen, i, '@OUTPUT@'],
                           output: name + i + '.c')
endforeach

shared_library('sharedlib', sources)
static_library('staticlib', sources)
executable('app', 'main.c', sources)
