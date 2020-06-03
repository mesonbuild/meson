project('very long command lines', 'c')

# Get the current system's commandline length limit.
if build_machine.system() == 'windows'
  # Various limits on windows:
  # cmd.exe: 8kb
  # CreateProcess: 32kb
  limit = 32767
elif build_machine.system() == 'cygwin'
  # cygwin-to-win32: see above
  # cygwin-to-cygwin: no limit?
  # Cygwin is slow, so only test it lightly here.
  limit = 8192
else
  # ninja passes whole line as a single argument, for which
  # the limit is 128k as of Linux 2.6.23.  See MAX_ARG_STRLEN.
  # BSD seems similar, see https://www.in-ulm.de/~mascheck/various/argmax
  limit = 131072
endif
# Now exceed that limit, but not so far that the test takes too long.
name = 'ALongFilenameMuchLongerThanIsNormallySeenAndReallyHardToReadThroughToTheEndAMooseOnceBitMySisterSheNowWorksAtLLamaFreshFarmsThisHasToBeSoLongThatWeExceed128KBWithoutCompilingTooManyFiles'
namelen = 187
nfiles = 50 + limit / namelen
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

# Also test short commandlines to make sure that doesn't regress
shared_library('sharedlib0', sources[0])
static_library('staticlib0', sources[0])
executable('app0', 'main.c', sources[0])
