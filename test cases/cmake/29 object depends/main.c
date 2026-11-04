int object_depends_absolute(void);
int object_depends_relative(void);
int object_depends_subdir(void);
int object_depends_transitive(void);

int main(void)
{
    if (object_depends_absolute() != 1) {
        return 1;
    }
    if (object_depends_relative() != 2) {
        return 2;
    }
    if (object_depends_subdir() != 3) {
        return 3;
    }
    if (object_depends_transitive() != 4) {
        return 4;
    }
    return 0;
}
