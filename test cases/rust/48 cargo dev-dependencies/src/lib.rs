pub fn value() -> u32 {
    mylib::value()
}

#[cfg(test)]
mod tests {
    #[test]
    fn uses_dev_dependency() {
        assert_eq!(testutil::expected(), 3);
    }
}
