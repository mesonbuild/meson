#![no_std]

#[no_mangle]
pub extern "C" fn rust_function() -> i32 {
    0
}

#[panic_handler]
fn panic(_info: &core::panic::PanicInfo) -> ! {
    loop {}
}
