# SPDX-License-Identifier: Apache-2.0
# Copyright © 2021 Intel Corporation

project('rust wrong link language', 'c')

if not add_languages('rust', required: false)
  error('MESON_SKIP_TEST test requires rust compiler')
endif

executable('f', 'f.rs', link_language: 'c')
