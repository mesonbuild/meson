#[no_mangle]
pub extern "C" fn r3() -> i32 {
    r1::r1() + r2::r2()
}
