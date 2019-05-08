from setuptools import setup, find_packages
from qbittorrentapi import VERSION

with open("README.rst", "r") as fh:
    long_description = fh.read()

setup(
    name='qbittorrent-api',
    version=VERSION,
    packages=find_packages(exclude=["*.tests", "*.tests.*", "tests.*", "tests"]),
    include_package_data=True,
    install_requires=['attrdict', 'requests'],
    url='https://github.com/rmartin16/qbittorrent-api',
    license='GPL-3',
    author='Russell Martin',
    author_email='rmartin16@gmail.com',
    description='Python client implementation for qBittorrent Web API v2 first available in qBittorrent v4.1.',
    long_description=long_description,
    keywords='qbittorrent api',
    zip_safe=False,
    classifiers=["Programming Language :: Python :: 3",
                 "Programming Language :: Python :: 2",
                 'Development Status :: 4',
                 'Environment :: Console',
                 'Intended Audience :: Developers,'
                 "Operating System :: OS Independent"]
)
