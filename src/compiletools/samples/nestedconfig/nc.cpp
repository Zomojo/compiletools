// A simple C++ app that compiles with C98
// This exists to show that the local config overrides the repo wide defaults

int func(int value)
{
    return value * 42;
}

int main(int argc, char* argv[])
{
    return func(argc);
}

