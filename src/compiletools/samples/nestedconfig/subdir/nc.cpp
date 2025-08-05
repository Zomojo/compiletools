// A simple C++ app that compiles with C17
// This exists to show that the local config overrides the repo wide defaults

template <auto>
struct MyStruct
{
};


int main(int argc, char* argv[])
{
    MyStruct<5> valint;
    MyStruct<'c'> valchar;
    return 0;
}

