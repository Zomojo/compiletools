// Simple test for pkg-config

//#CXXFLAGS=-std=c++17
#include <cstring>
#include <zlib.h>
// The libsystemd is here to make sure multiple packages on one line are OK
//#PKG-CONFIG=zlib libsystemd

int main(int argc, char* argv[])
{
    unsigned char input[] = "Hello Hello Hello Hello Hello Hello!"; 
    unsigned char compressed[50];
    
    // zlib struct
    z_stream defstream;
    defstream.zalloc = Z_NULL;
    defstream.zfree = Z_NULL;
    defstream.opaque = Z_NULL;
    // setup "a" as the input and "b" as the compressed output
    defstream.avail_in = static_cast<uInt>(sizeof(input)+1); // size of input, string + terminator
    defstream.next_in = reinterpret_cast<Bytef *>(&input[0]); // input char array
    defstream.avail_out = static_cast<uInt>(sizeof(compressed)); // size of output
    defstream.next_out = static_cast<Bytef *>(&compressed[0]); // output char array
    
    // the actual compression work.
    deflateInit(&defstream, Z_BEST_COMPRESSION);
    deflate(&defstream, Z_FINISH);
    deflateEnd(&defstream);
}

