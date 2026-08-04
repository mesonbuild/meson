extern "C" {
    fn get_value() -> i32;
}

fn main() {
    println!("{}", unsafe { get_value() });
}
