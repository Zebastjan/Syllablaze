from setuptools import setup
from constants import APP_VERSION

setup(
    name="syllablaze",
    version=APP_VERSION,
    py_modules=["main"],
    install_requires=open("requirements.txt").read().splitlines(),
    entry_points={
        "console_scripts": [
            "syllablaze=main:main",
        ],
    },
)