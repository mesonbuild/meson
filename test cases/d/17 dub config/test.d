module test;

version(Have_openssl)
{
    static assert(false, "vibe:tls should be with config notls");
}

void main() {}
