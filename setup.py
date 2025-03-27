
from setuptools import setup, find_packages
import os
import sys

# Add the current directory to the path so we can import from blaze
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from blaze.constants import APP_VERSION

setup(
    name="syllablaze",
    version=APP_VERSION,
    packages=find_packages(),
    install_requires=open("requirements.txt").read().splitlines(),
    entry_points={
        "console_scripts": [
            "syllablaze=blaze.main:main",
        ],
    },
)
