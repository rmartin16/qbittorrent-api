from setuptools import setup, find_packages
from qbittorrentapi import VERSION

with open("README.rst", "r") as fh:
    long_description = fh.read()

setup(
    name='qbittorrent-api',
    version=VERSION,
    packages=find_packages(exclude=('tests',)),
    install_requires=('attrdict', 'requests'),
    url='https://github.com/rmartin16/qbittorrent-api',
    license='GPL-3',
    author='Russell Martin',
    author_email='rmartin16@gmail.com',
    description='Python client implementation for qBittorrent Web API v2 first available in qBittorrent v4.1.',
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords='qbittorrent api',
    classifiers=["Programming Language :: Python :: 3",
                 "Programming Language :: Python :: 2",
                 "Operating System :: OS Independent"]
)
