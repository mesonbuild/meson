using System;
using System.IO;

public class Prog {
    static public void Main (string[] args) {
        LibB.Hello();
        if (args.Length > 0) {
            using (var sw = new StreamWriter(args[0])) {
                sw.WriteLine("Hello World");
            }
        }
    }
}
