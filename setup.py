from setuptools import setup, find_packages
import os
import io

here = os.path.abspath(os.path.dirname(__file__))

# Get the long description from the README file
with io.open(os.path.join(here, 'README.rst'), encoding='utf-8') as ff:
    long_description = ff.read()

setup(
    name='compiletools',
    use_scm_version=True,
    setup_requires=[
        'setuptools_scm',
        'setuptools_scm_git_archive'],
    description='Tools to make compiling C/C++ projects easy',
    long_description=long_description,
    url='http://zomojo.github.io/compiletools/',
    author='Zomojo Pty Ltd',
    author_email='geoff@zomojo.com',
    license='GPLv3+',
    classifiers=[
            'Development Status :: 4 - Beta',
            'Intended Audience :: Developers',
            'Topic :: Software Development :: Build Tools',
            'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
            'Programming Language :: Python :: 2.7',
            'Programming Language :: Python :: 3',
    ],
    keywords='c++ make development',
    packages=find_packages(),
    install_requires=[
        'configargparse',
        'appdirs',
        'docutils'],
    test_suite="ct",
    scripts=[
        ff for ff in os.listdir('.') if ff.startswith('ct-')])
