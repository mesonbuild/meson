// This file builds with 2018, the default for this project
const fn increment(x: i32) -> i32 {
    return x + 1;
}

const VALUE: i32 = increment(2);

pub fn main() {
    std::process::exit(VALUE - 3);
}
