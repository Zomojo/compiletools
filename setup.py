from setuptools import setup, find_packages
import os
import io
from ct.version import __version__

here = os.path.abspath(os.path.dirname(__file__))

# Get the long description from the README file
with io.open(os.path.join(here, "ct", "README.ct-doc.rst"), encoding="utf-8") as ff:
    long_description = ff.read()

setup(
    name="compiletools",
    version=__version__,
    description="Tools to make compiling C/C++ projects easy",
    long_description=long_description,
    long_description_content_type="text/x-rst",
    url="http://zomojo.github.io/compiletools/",
    python_requires=">=3.9",  # Updated minimum Python version
    author="Zomojo Pty Ltd",
    author_email="drgeoffathome@gmail.com",
    license="GPLv3+",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13"
    ],
    keywords="c++ make development",
    packages=find_packages(),
    package_data={"":[ff for ff in os.listdir("ct") if ff.startswith("README")]},
    include_package_data=True,
    install_requires=[
        "configargparse>=1.5.3",
        "appdirs>=1.4.4",
        "psutil>=5.9.0",
        "rich>=12.0.0",
        "rich_rst>=1.1.7",
    ],
    test_suite="ct",
    scripts=[ff for ff in os.listdir(".") if ff.startswith("ct-")],
    download_url="https://github.com/Zomojo/compiletools/archive/v"
    + __version__
    + ".tar.gz",
)
