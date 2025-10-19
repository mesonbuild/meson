// SPDX-License-Identifier: Apache-2.0
// Copyright © 2021 Intel Corporation

#![allow(non_upper_case_globals)]
#![allow(non_camel_case_types)]
#![allow(non_snake_case)]

include!("internal_dep.rs");

use std::convert::TryInto;

fn main() {
    unsafe {
        std::process::exit(add64(0, 0).try_into().unwrap_or(5));
    };
}
