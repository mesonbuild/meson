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
