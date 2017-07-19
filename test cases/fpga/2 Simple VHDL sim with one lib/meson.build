project('simple vhdl', 'c')
fpga = import('fpga')

mylib=fpga.library('mylib',packages:'mylib/mypackage/mypackage.vhd',sources:'mylib/mypackage/adder.vhd')

fpga.simulation('adder_testbench','adder_testbench.vhd',simulator:'GHDL',depends:mylib)


