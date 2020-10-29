pub fn print_str() -> String {
    return "A String".to_string();
}

#[cfg(feature = "test_feature")]
pub fn returncode() -> i32 {
    return 0;
}

#[cfg(not(feature = "test_feature"))]
pub fn returncode() -> i32 {
    return 1;
}

#[cfg(feature = "default_feature")]
pub fn default_rc() -> i32 {
    return 0;
}

#[cfg(not(feature = "default_feature"))]
pub fn default_rc() -> i32 {
    return 1;
}
