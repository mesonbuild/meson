// No includes here, they need to come from the PCH

int main(int argc, char **argv) {
    // Method is implemented in pch.c.
    // This makes sure that we can properly handle user defined
    // pch implementation files and not only auto-generated ones.
    return foo();
}
