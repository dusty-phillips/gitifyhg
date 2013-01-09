# Copyright 2012 Dusty Phillips

# This file is part of gitifyhg.

# gitifyhg is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# gitifyhg is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with gitifyhg.  If not, see <http://www.gnu.org/licenses/>.


from setuptools import setup
setup(
    name="gitifyhg",
    author="Dusty Phillips",
    author_email="dusty@buchuki.com",
    url="https://github.com/buchuki/gitifyhg",
    description="Use git as client for hg repos",
    version="0.6.2",
    py_modules=["gitifyhg"],
    install_requires=[
        'path.py',
        'Mercurial',
    ],
    entry_points={
        'console_scripts': [
            'git-remote-gitifyhg = gitifyhg:main',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development :: Version Control',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
    ]
)
