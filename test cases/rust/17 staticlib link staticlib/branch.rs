#[no_mangle]
pub extern "C" fn what_have_we_here() -> i32 {
    leaf::HOW_MANY * leaf::HOW_MANY
}
