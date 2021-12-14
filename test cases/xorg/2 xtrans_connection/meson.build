project('xorg xtrans connection')

xorg = import('unstable-xorg')

conf = xorg.xtrans_connection()
assert(conf.has('TCPCONN'), 'TCP connection not enabled?')
if host_machine.system() != 'windows'
  assert(conf.has('UNIXCONN'), 'UNIX connection not enabled on unix-like OS?')
endif
if host_machine.system() == 'sunos'
  assert(conf.has('LOCALCONN'), 'Local connection not enabled on Solaris/Illumos?')
endif
