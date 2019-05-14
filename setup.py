from setuptools import setup, find_packages
from qbittorrentapi import VERSION

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name='qbittorrent-api',
    version=VERSION,
    packages=find_packages(exclude=["*.tests", "*.tests.*", "tests.*", "tests"]),
    include_package_data=True,
    install_requires=['attrdict<=2.0.1,>=2.0.0',
                      'requests>=2.16.0,<=2.21.0',
                      'urllib3>=1.24.2,<=1.24.3 '],
    url='https://github.com/rmartin16/qbittorrent-api',
    author='Russell Martin',
    author_email='rmartin16@gmail.com',
    description='Python wrapper for qBittorrent 4.1+ (Web API v2.2+)',
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords='qbittorrent api',
    zip_safe=False,
    license='GPL-3',
    classifiers=["Programming Language :: Python :: 3.7",
                 "Programming Language :: Python :: 3.6",
                 "Programming Language :: Python :: 3.5",
                 "Programming Language :: Python :: 3.4",
                 "Programming Language :: Python :: 2.7",
                 "Programming Language :: Python :: 2.6",
                 "Development Status :: 4 - Beta",
                 "Environment :: Console",
                 "Intended Audience :: Developers",
                 "Operating System :: OS Independent",
                 'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
                 "Topic :: Communications :: File Sharing",
                 "Topic :: Utilities"
                 ]
)
