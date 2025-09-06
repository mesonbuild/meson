extern crate m1;

#[no_mangle]
pub extern "C" fn foo() -> i32 {
    m1::member1() + 1
}
