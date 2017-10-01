class MainProg : GLib.Object {

    public static int main(string[] args) {
        var test1 = new Test ();
        var test2 = new Subdir.Test ();
        stdout.printf("Vala is working.\n");
        return 0;
    }
}
