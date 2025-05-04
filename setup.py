
from setuptools import setup, find_packages
import os
import sys

# Read requirements.txt and filter out empty lines/comments
with open("requirements.txt") as req_file:
    requirements = [
        line.strip()
        for line in req_file
        if line.strip() and not line.startswith('#')
    ]

setup(
    name="syllablaze",
    version="0.3",  # Hardcoded version for now
    packages=find_packages(),
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "syllablaze=blaze.main:main",
        ],
    },
)
