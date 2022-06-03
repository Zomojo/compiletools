from setuptools import setup, find_packages
import os
import glob
import io
from ct.version import __version__

here = os.path.abspath(os.path.dirname(__file__))

# Get the long description from the README file
with io.open(os.path.join(here, "ct", "README.ct-doc.rst"), encoding="utf-8") as ff:
    long_description = ff.read()

setup(
    name="compiletools",
    version=__version__,
    setup_requires=["setuptools_scm"],
    description="Tools to make compiling C/C++ projects easy",
    long_description=long_description,
    url="http://zomojo.github.io/compiletools/",
    python_requires=">=3.6",
    author="Zomojo Pty Ltd",
    author_email="drgeoffathome@gmail.com",
    license="GPLv3+",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Programming Language :: Python :: 3",
    ],
    keywords="c++ make development",
    packages=find_packages(),
    package_data={"":[ff for ff in os.listdir("ct") if ff.startswith("README")]},
    include_package_data=True,
    install_requires=["configargparse", "appdirs", "psutil", "rich", "rich_rst"],
    test_suite="ct",
    scripts=[ff for ff in os.listdir(".") if ff.startswith("ct-")],
    download_url="https://github.com/Zomojo/compiletools/archive/v"
    + __version__
    + ".tar.gz",
)

