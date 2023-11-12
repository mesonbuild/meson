#[no_mangle]
pub extern "C" fn rust_func() -> i32 {
    mybar::VALUE
}
