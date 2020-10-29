project('cargo functional tests', 'rust')

rust = import('unstable-rust')

# Test manual tests here
rust.subproject('sub1')

# Test auto tests here
rust.subproject('sub2')

# Test mixing auto and manual, using 2015 rules
rust.subproject('sub3')

# Test mixing auto and manual, using 2018 rules
rust.subproject('sub4')
