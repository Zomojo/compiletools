#pragma once
#include <string>

struct widget
{
    virtual std::string as_string() const = 0;
};
