// SPDX-License-Identifier: Apache-2.0
// Copyright © 2023 Intel Corporation

#![allow(non_upper_case_globals)]
#![allow(non_camel_case_types)]
#![allow(non_snake_case)]

include!("global-project.rs");

fn main() {
    unsafe {
        std::process::exit(success());
    };
}
