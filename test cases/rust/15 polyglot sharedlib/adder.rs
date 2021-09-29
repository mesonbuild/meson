#[repr(C)]
pub struct Adder {
  pub number: i32
}

#[no_mangle]
pub extern fn adder_add(a: &Adder, number: i32) -> i32 {
    return a.number + number;
}
