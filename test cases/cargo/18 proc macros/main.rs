extern crate sub1;
use sub1::make_answer;

make_answer!();

fn main() {
    std::process::exit(answer() - 42);
}
