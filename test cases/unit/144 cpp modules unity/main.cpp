extern "C" int mod_value();
int a_value();
int b_value();

int main() { return mod_value() + a_value() + b_value() == 6 ? 0 : 1; }
