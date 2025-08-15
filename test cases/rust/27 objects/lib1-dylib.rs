extern "C" {
    fn from_lib1();
}

#[no_mangle]
extern "C" fn from_lib2()
{
    println!("hello world from rust");
}

#[no_mangle]
pub extern "C" fn c_func()
{
    unsafe { from_lib1(); }
}

/// ```
/// use lib12::rust_func;
/// rust_func();
/// ```
pub fn rust_func()
{
    unsafe { from_lib1(); }
}
