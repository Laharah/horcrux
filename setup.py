#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages

VERSION = 1.0.3

with open("README.md") as readme_file:
    readme = readme_file.read()

requirements = [
    "pynacl",
    "protobuf>=3.0.0",
    "rich",
]

setup_requirements = [
    "pytest-runner",
]

test_requirements = [
    "pytest>=3",
]

setup(
    author="Laharah",
    author_email="laharah22@gmail.com",
    python_requires=">=3.5",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    description="Split a file into n encrypted horcruxes, that can only be decrypted by re-combining k of them.",
    entry_points={
        "console_scripts": [
            "horcrux=horcrux.cli:main",
        ],
    },
    install_requires=requirements,
    license="MIT license",
    long_description=readme,
    include_package_data=True,
    keywords="horcrux",
    name="horcrux",
    packages=find_packages(include=["horcrux", "horcrux.*"]),
    setup_requires=setup_requirements,
    test_suite="tests",
    tests_require=test_requirements,
    url="https://github.com/laharah/horcrux",
    version=VERSION,
    zip_safe=False,
)
