#![no_main]

#[no_mangle]
pub extern "C" fn hello_rust() {
    println!("hello world");
}
