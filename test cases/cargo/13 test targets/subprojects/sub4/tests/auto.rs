extern crate mylib;

pub fn main() {
    let a = mylib::add(1, -12);
    let b = a + 11;
    std::process::exit(b);
}
