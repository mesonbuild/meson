project('pcap test', 'c')

pcap_dep = dependency('pcap', version : '>=1.0')

e = executable('pcap_prog', 'pcap_prog.c', dependencies : pcap_dep)

test('pcaptest', e)
