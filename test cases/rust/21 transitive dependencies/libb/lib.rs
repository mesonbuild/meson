// no_mangle included for the case where libb is used as a staticlib.
#[no_mangle]
pub extern "C" fn bar() -> i32 {
    2 * liba::foo()
}
