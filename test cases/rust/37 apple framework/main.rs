extern crate timelib;

fn main() {
    let time = timelib::get_absolute_time();
    println!("Current CFAbsoluteTime: {}", time);
}
