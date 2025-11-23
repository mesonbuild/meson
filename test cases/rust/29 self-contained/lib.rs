#[unsafe(export_name = "hello")]
pub extern "C" fn hello() {
    println!("Hello, world!");
}
