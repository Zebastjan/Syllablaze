from setuptools import setup

setup(
    name="syllablaze",
    version="0.1.0",
    py_modules=["main"],
    install_requires=open("requirements.txt").read().splitlines(),
    entry_points={
        "console_scripts": [
            "syllablaze=main:main",
        ],
    },
)