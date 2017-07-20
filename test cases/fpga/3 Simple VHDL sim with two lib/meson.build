project('simple vhdl', 'c')
fpga = import('fpga')

mylib=fpga.library('mylib',packages:'mylib/mypackage/mypackage.vhd',sources:'mylib/mypackage/adder.vhd')

mylib2=fpga.library('mylib2',
                  packages:'mylib2/mypackage/mypackage.vhd',
                  sources:'mylib2/mypackage/adder.vhd',
                  depends:mylib
                  )


fpga.simulation('adder_testbench','adder_testbench.vhd',simulator:'GHDL',depends:mylib2)


