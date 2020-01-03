from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name='qbittorrent-api',
    version="0.5.1",
    packages=find_packages(exclude=["*.tests", "*.tests.*", "tests.*", "tests"]),
    include_package_data=True,
    install_requires=['attrdict>=2.0.0',
                      'requests>=2.16.0',
                      'urllib3>=1.24.2'],
    url='https://github.com/rmartin16/qbittorrent-api',
    author='Russell Martin',
    description='Python client for qBittorrent v4.1+ Web API',
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords='qbittorrent api',
    zip_safe=False,
    license='GPL-3',
    classifiers=["Programming Language :: Python :: 3.8",
                 "Programming Language :: Python :: 3.7",
                 "Programming Language :: Python :: 3.6",
                 "Programming Language :: Python :: 3.5",
                 "Programming Language :: Python :: 3.4",
                 "Programming Language :: Python :: 2.7",
                 "Programming Language :: Python :: 2.6",
                 "Development Status :: 5 - Production/Stable",
                 "Environment :: Console",
                 "Intended Audience :: Developers",
                 "Operating System :: OS Independent",
                 'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
                 "Topic :: Communications :: File Sharing",
                 "Topic :: Utilities"
                 ]
)
