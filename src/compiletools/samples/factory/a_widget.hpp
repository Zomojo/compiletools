#pragma once
#include "widget.hpp"

struct a_widget : widget
{
    virtual std::string as_string() const override;
};
