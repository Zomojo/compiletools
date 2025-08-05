#pragma once
#include "widget.hpp"

struct z_widget : widget
{
    virtual std::string as_string() const override;
};
