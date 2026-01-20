extern crate stuff;

extern "C" {
    fn not_so_rusty() -> i64;
}

fn main() {
    println!("printing: {} {}", stuff::explore(), unsafe {
        not_so_rusty()
    });
}
