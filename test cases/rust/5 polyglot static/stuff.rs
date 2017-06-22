#![crate_name = "stuff"]

#[no_mangle]
pub extern fn f() {
    println!("Hello from Rust!");
}
