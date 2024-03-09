extern crate common;

extern "C" {
    fn extra_func() -> i32;
}

#[cfg(feature = "foo")]
#[no_mangle]
pub extern "C" fn rust_func() -> i32 {
    assert!(common::common_func() == 0);
    let v: i32;
    unsafe {
         v = extra_func();
    };
    mybar::VALUE + v
}
