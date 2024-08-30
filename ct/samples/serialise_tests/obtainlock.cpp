#include "obtainlock.hpp"
#include "filename.hpp"
#include <fstream>
#include <fcntl.h>
#include <stdexcept>
#include <unistd.h>
#include <thread>
#include <chrono>

void obtainlock()
{
    int fd = open(filename, O_RDWR);
    if (fd == -1) {
        throw std::runtime_error("Error: Could not open the file");
    }

    struct flock fl;
    fl.l_type = F_WRLCK; // Write lock
    fl.l_whence = SEEK_SET;
    fl.l_start = 0;
    fl.l_len = 0; // Lock the entire file

    if (fcntl(fd, F_SETLK, &fl) == -1) {
        throw std::runtime_error("SerialiseTests Error: Could not acquire the file lock. This means the tests ran in parallel!");
    }

    std::this_thread::sleep_for(std::chrono::seconds(1));

    fl.l_type = F_UNLCK; // Unlock
    fcntl(fd, F_SETLK, &fl);

    close(fd);
}