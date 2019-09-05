// No includes here, they need to come from the PCH

void func() {
    fprintf(stdout, "This is a function that fails if stdio is not #included.\n");
}

int main() {
    return 0;
}

