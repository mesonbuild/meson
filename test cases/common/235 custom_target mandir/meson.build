# SPDX-license-identifier: Apache-2.0
# Copyright © 2021 Intel Corporation

project('custom_target mandir')

prog_py = import('python').find_installation()

custom_target(
  'man page',
  input : ['copy.py', 'page.1.in'],
  output : 'page.1',
  command : [prog_py, '@INPUT@', '@OUTPUT@'],
  install : true,
  install_dir : '@MANDIR@',
)

# Multiple outputs
custom_target(
  'multiple man page',
  input : ['copy.py', 'page.1.in'],
  output : ['page.4', 'page.5'],
  command : [prog_py, '@INPUT0@', '@INPUT1@', '@OUTPUT0@', '@INPUT1@', '@OUTPUT1@'],
  install : true,
  install_dir : ['@MANDIR@', '@MANDIR@'],
)

# Multiple outputs, single install_dir directive
custom_target(
  'multiple man page one output',
  input : ['copy.py', 'page.1.in'],
  output : ['page.2', 'page.3'],
  command : [prog_py, '@INPUT0@', '@INPUT1@', '@OUTPUT0@', '@INPUT1@', '@OUTPUT1@'],
  install : true,
  install_dir : '@MANDIR@',
)

configure_file(
  input : 'page.1.in',
  output : 'page.8',
  copy : true,
  install : true,
  install_dir : '@MANDIR@',
)
