use hello::{farewell, greet};

fn main() {
    println!("{}", greet());
    println!("{}", farewell());
    println!("{}", answer::answer());
    println!("{}", answer::large_answer());
}
