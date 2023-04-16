use std::os::raw::c_int;

#[no_mangle]
pub unsafe extern "C" fn print_foo() -> c_int {
    let foo = "rust compiler is working";
    println!("{}", foo);
    0
}
