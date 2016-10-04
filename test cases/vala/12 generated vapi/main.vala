using Foo;
using Bar;

class Main : GLib.Object {
    public static int main(string[] args) {
        var ignore = Foo.return_success();
        return Bar.return_success();
    }
}
