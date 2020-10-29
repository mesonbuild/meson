pub fn main() {
    std::process::exit(value());
}

fn value() -> i32 {
    return 0;
}

#[test]
fn test_value() {
    let r = value();
    assert_eq!(r, 0, "did not get 0")
}
