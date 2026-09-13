pub fn value() -> u32 {
    1
}

#[cfg(test)]
mod tests {
    #[test]
    fn uses_dev_dependency() {
        assert_eq!(b::doubled(), 2);
    }
}
