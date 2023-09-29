fn main() {
    let foo = "rust compiler is working";
    let bar = include_bytes!("data.txt");
    println!("{} and {}", foo, String::from_utf8_lossy(bar));
}
