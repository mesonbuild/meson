#[no_mangle]
pub extern "C" fn get_value() -> i32 {
    lib::hello()
}
