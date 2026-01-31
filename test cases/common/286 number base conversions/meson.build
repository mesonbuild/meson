project('test number base conversions')

### .to_int()

# hexadecimal strings
assert('0x10'.to_int() == 16, 'Hex string conversion failed')
assert('0X10'.to_int() == 16, 'Hex string conversion (uppercase X) failed')
assert('0xff'.to_int() == 255, 'Hex string conversion (lowercase) failed')
assert('0xFF'.to_int() == 255, 'Hex string conversion (uppercase) failed')
assert('0xDEADBEEF'.to_int() == 3735928559, 'Large hex conversion failed')
assert('0x1'.to_int() == 1, 'Small hex conversion failed')
assert('0x0'.to_int() == 0, 'Zero hex conversion failed')

# signed hexadecimal strings
assert('-0xf'.to_int() == -15, 'Negative hex string conversion failed')
assert('+0x10'.to_int() == 16, 'Positive hex string conversion failed')
assert('-0xFF'.to_int() == -255, 'Negative hex string (uppercase) conversion failed')

# octal strings
assert('0o10'.to_int() == 8, 'Octal string conversion failed')
assert('0O10'.to_int() == 8, 'Octal string conversion (uppercase O) failed')
assert('0o77'.to_int() == 63, 'Octal string conversion failed')
assert('0o755'.to_int() == 493, 'Octal permission-like conversion failed')
assert('0o0'.to_int() == 0, 'Zero octal conversion failed')

# signed octal strings
assert('-0o10'.to_int() == -8, 'Negative octal string conversion failed')
assert('+0o77'.to_int() == 63, 'Positive octal string conversion failed')

# binary strings
assert('0b10'.to_int() == 2, 'Binary string conversion failed')
assert('0B10'.to_int() == 2, 'Binary string conversion (uppercase B) failed')
assert('0b1111'.to_int() == 15, 'Binary string conversion failed')
assert('0b11111111'.to_int() == 255, 'Binary byte conversion failed')
assert('0b0'.to_int() == 0, 'Zero binary conversion failed')

# signed binary strings
assert('-0b101'.to_int() == -5, 'Negative binary string conversion failed')
assert('+0b1111'.to_int() == 15, 'Positive binary string conversion failed')

# decimal strings (backwards compat)
assert('10'.to_int() == 10, 'Decimal string conversion failed')
assert('255'.to_int() == 255, 'Decimal string conversion failed')
assert('0'.to_int() == 0, 'Zero decimal conversion failed')
assert('12345'.to_int() == 12345, 'Large decimal conversion failed')

# leading zeroes are decimal (backwards compat)
assert('010'.to_int() == 10, 'Decimal with leading zero broke backward compatibility')
assert('0123'.to_int() == 123, 'Decimal with leading zeros broke backward compatibility')
assert('007'.to_int() == 7, 'Decimal with leading zeros broke backward compatibility')

### .to_string()

# hex format
assert(16.to_string(format: 'hex') == '0x10', 'Int to hex string failed')
assert(255.to_string(format: 'hex') == '0xff', 'Int to hex string failed')
assert(0.to_string(format: 'hex') == '0x0', 'Zero to hex string failed')
assert(1.to_string(format: 'hex') == '0x1', 'One to hex string failed')
assert(3735928559.to_string(format: 'hex') == '0xdeadbeef', 'Large hex string failed')

# octal format
assert(8.to_string(format: 'oct') == '0o10', 'Int to octal string failed')
assert(63.to_string(format: 'oct') == '0o77', 'Int to octal string failed')
assert(493.to_string(format: 'oct') == '0o755', 'Permission to octal string failed')
assert(0.to_string(format: 'oct') == '0o0', 'Zero to octal string failed')

# binary format
assert(2.to_string(format: 'bin') == '0b10', 'Int to binary string failed')
assert(15.to_string(format: 'bin') == '0b1111', 'Int to binary string failed')
assert(255.to_string(format: 'bin') == '0b11111111', 'Byte to binary string failed')
assert(0.to_string(format: 'bin') == '0b0', 'Zero to binary string failed')

# decimal format (explicit)
assert(10.to_string(format: 'dec') == '10', 'Int to decimal string failed')
assert(255.to_string(format: 'dec') == '255', 'Int to decimal string failed')

# default
assert(42.to_string() == '42', 'Default int to string failed')

# fill and hex format
assert(255.to_string(format: 'hex', fill: 8) == '0x0000ff', 'Hex with fill failed')
assert(1.to_string(format: 'hex', fill: 6) == '0x0001', 'Hex with fill failed')
assert(255.to_string(format: 'hex', fill: 4) == '0xff', 'Hex with fill (no padding needed) failed')

# fill and other formats
assert(8.to_string(format: 'oct', fill: 6) == '0o0010', 'Octal with fill failed')
assert(2.to_string(format: 'bin', fill: 10) == '0b00000010', 'Binary with fill failed')

# negative numbers
assert((-15).to_string(format: 'hex') == '-0xf', 'Negative hex conversion failed')
assert((-8).to_string(format: 'oct') == '-0o10', 'Negative octal conversion failed')
assert((-5).to_string(format: 'bin') == '-0b101', 'Negative binary conversion failed')

# negative numbers and fill
assert((-15).to_string(format: 'hex', fill: 6) == '-0x00f', 'Negative hex with fill failed')
assert((-8).to_string(format: 'oct', fill: 7) == '-0o0010', 'Negative octal with fill failed')
assert((-5).to_string(format: 'bin', fill: 8) == '-0b00101', 'Negative binary with fill failed')
assert((-4).to_string(fill: 3) == '-04', 'Negative decimal with fill failed')

# fill and decimal
assert(4.to_string(fill: 3) == '004', 'Decimal with fill failed')

### Round trip conversions

# positive

hex_val = 0x200
hex_str = hex_val.to_string(format: 'hex')
assert(hex_str.to_int() == hex_val, 'Hex round-trip failed')

oct_val = 0o755
oct_str = oct_val.to_string(format: 'oct')
assert(oct_str.to_int() == oct_val, 'Octal round-trip failed')

bin_val = 0b11010
bin_str = bin_val.to_string(format: 'bin')
assert(bin_str.to_int() == bin_val, 'Binary round-trip failed')

# negative

neg_hex = -255
neg_hex_str = neg_hex.to_string(format: 'hex')
assert(neg_hex_str.to_int() == neg_hex, 'Negative hex round-trip failed')

neg_oct = -63
neg_oct_str = neg_oct.to_string(format: 'oct')
assert(neg_oct_str.to_int() == neg_oct, 'Negative octal round-trip failed')

neg_bin = -15
neg_bin_str = neg_bin.to_string(format: 'bin')
assert(neg_bin_str.to_int() == neg_bin, 'Negative binary round-trip failed')
