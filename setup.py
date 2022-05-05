from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="qbittorrent-api",
    version="2022.5.31",
    packages=find_packages(exclude=["*.tests", "*.tests.*", "tests.*", "tests"]),
    include_package_data=True,
    install_requires=[
        "requests>=2.16.0",
        "urllib3>=1.24.2",
        "six",
        'enum34; python_version < "3"',
    ],
    url="https://github.com/rmartin16/qbittorrent-api",
    author="Russell Martin",
    description="Python client for qBittorrent v4.1+ Web API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords="python qbittorrent api client torrent torrents",
    zip_safe=False,
    license="MIT",
    classifiers=[
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: MIT License",
        "Topic :: Communications :: File Sharing",
        "Topic :: Utilities",
    ],
)
