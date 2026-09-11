pub fn value() -> u32 {
    1
}

#[cfg(feature = "extra")]
pub fn extra_value() -> u32 {
    2
}
