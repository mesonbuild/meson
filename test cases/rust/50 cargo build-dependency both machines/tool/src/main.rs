use std::env;
use std::fs;

fn main() {
    let out = env::args().nth(1).expect("usage: tool OUTPUT");
    let contents = format!("pub fn generated() -> u32 {{ {} }}\n", shared::value());
    fs::write(out, contents).expect("cannot write output");
}
