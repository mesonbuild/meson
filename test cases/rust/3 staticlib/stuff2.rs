#![crate_name = "stuff2"]

extern crate other;

extern "C" {
    fn c_explore_value() -> i32;
}

pub fn explore(
) -> String {
    unsafe {
        other::explore(c_explore_value())
    }
}
