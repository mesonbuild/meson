# SPDX-License-Identifier: Apache-2.0
# Copyright © 2023 Intel Corporation

project('sanitizer', 'c', meson_version : '>= 1.4')

assert(get_option('b_sanitize') == 'address,undefined', 'order of address + undefined is not correct')

array = get_option('b_sanitizers')
assert('address' in array)
assert('undefined' in array)
