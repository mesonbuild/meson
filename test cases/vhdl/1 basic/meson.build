project('simple vhdl', 'c')

e = fpga_bitstream('simple-adder', 'adder.vhd',
     device:'DEVICE_DIE_REF',
     toolchain:'ISE',
     constraints:['led.ucf','led.xcf'],
     dependencies:'',
     synth_options:'some options',
     map_options:'some options',
     pr_options:'some options'
)

#test('Simple Test','testbench.vhd', src ,simulator:'GHDL',args:'--vcd=output.vcd')

