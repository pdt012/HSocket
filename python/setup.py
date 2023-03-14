# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

NAME = "hsocket"
VERSION = "0.3.0"
DESCRIPTION = "hsocket for python"
AUTHOR = "pdt012"
AUTHOR_EMAIL = "jxh0615@163.com"
URL = "https://github.com/pdt012/HSocket"

setup(
    name=NAME,
    version=VERSION,
    description=DESCRIPTION,
    author=AUTHOR,
    author_email=AUTHOR_EMAIL,
    url=URL,
    packages=find_packages("src"),
    package_dir={"": "src"},
)
