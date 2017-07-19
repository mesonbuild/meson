project('simple vhdl', 'c')
fpga = import('fpga')

bitsream = fpga.bitstream('simple-adder', 'adder.vhd',
     device:'DEVICE_DIE_REF',
     toolchain:'ISE',
     constraints:['led.ucf','led.xcf'],
     dependencies:'',
     synth_options:'some options',
     map_options:'some options',
     pr_options:'some options'
)

fpga.simulation('adder','adder.vhd',simulator:'GHDL')


#test('Simple Test','testbench.vhd', src ,simulator:'GHDL',args:'--vcd=output.vcd')

