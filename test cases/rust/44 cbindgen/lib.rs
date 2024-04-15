/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright © 2024 Intel Corporation
 */

#[repr(C)]
pub struct MyStruct {
        pub cost: i64,
        pub power: u8,
}

#[no_mangle]
pub extern "C" fn print(x: &MyStruct) {
        println!("A thing has a cost of {} and a power of {}", x.cost, x.power);
}
