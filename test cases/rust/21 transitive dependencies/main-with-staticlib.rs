extern "C" { fn bar() -> i32; }

fn main() {
    println!("{}", unsafe { bar() });
}
