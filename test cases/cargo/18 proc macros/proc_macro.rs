extern crate sub1;
use proc_macro_examples::make_answer;

make_answer!();

fn main() {
    std::process::exit(answer() - 42);
}
