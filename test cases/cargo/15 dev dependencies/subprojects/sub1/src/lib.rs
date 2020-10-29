#[cfg(test)]
extern crate test_function;

pub fn function(x: i32) -> i32 {
    return x + 5;
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn with_sub() {
        let i = function(test_function::function());
        assert_eq!(i, 10);
    }
}

