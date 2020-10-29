extern crate mylib;

pub fn main() {
    let a = mylib::add(1, 2);
    let b = a - 3;
    std::process::exit(b);
}
