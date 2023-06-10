extern "C" {
    fn extra_func() -> i32;
}

#[no_mangle]
pub extern "C" fn rust_func() -> i32 {
    let v: i32;
    unsafe {
         v = extra_func();
    };
    mybar::VALUE + v
}
