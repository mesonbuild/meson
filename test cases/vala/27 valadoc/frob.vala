
/**
 * Example Valadoc comment for the Frob namespace.
 */
namespace Frob {

/**
 * Example Valadoc class comment for Animal.
 */
public class Animal : GLib.Object {

    /** Example valadoc comment for string property name */
    public string name { get; set; default = ""; }

    public Animal(string name) {
        this.name = name;
    }
}

/**
 * Example Valadoc class comment for Cat.
 *
 * Cat extends {@link Animal}.
 */
public class Cat : Animal {

    public Cat(string name) {
        base(name);
    }

    /**
     * My cat likes doing this at 3AM
     */
    public void meow() {
        print("Meow!");
    }
}
}
