extern crate zstdrs;

fn main() {
    let v = zstdrs::max_compression_level();
    println!("ZSTD maximum compression level is: {}", v);
}