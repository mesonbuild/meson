from limited import hello
from limited_with_lib import hello as hello_with_lib

def test_hello():
    assert hello() == "hello world"
    assert hello_with_lib() == "hello world"

test_hello()
