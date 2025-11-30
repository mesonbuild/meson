pub fn greet() -> &'static str
{
    "hello world"
}

#[cfg(feature = "goodbye")]
pub fn farewell() -> &'static str
{
    "goodbye"
}
