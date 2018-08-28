# encoding: utf-8
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Author: Kyle Lahnakoski (kyle@lahnakoski.com)
#
from distutils.util import convert_path
import os
from setuptools import setup


root = os.path.abspath(os.path.dirname(__file__))
path = lambda *p: os.path.join(root, *p)
try:
    long_desc = open(path('README.txt')).read()
except Exception:
    long_desc = "<Missing README.txt>"
    print("Missing README.txt")


def find_packages(where='.', lib_prefix='', exclude=()):
    """
    SNAGGED FROM distribute-0.6.49-py2.7.egg/setuptools/__init__.py
    """
    out = []
    stack=[(convert_path(where), lib_prefix)]
    while stack:
        where,prefix = stack.pop(0)
        for name in os.listdir(where):
            fn = os.path.join(where,name)
            if ('.' not in name and os.path.isdir(fn) and
                os.path.isfile(os.path.join(fn,'__init__.py'))
            ):
                out.append(prefix+name); stack.append((fn,prefix+name+'.'))
    for pat in list(exclude)+['ez_setup', 'distribute_setup']:
        from fnmatch import fnmatchcase
        out = [item for item in out if not fnmatchcase(item,pat)]
    return out




setup(
    name='mo-json-config',
    version="2.18.18240",
    description='More JSON Configuration! JSON configuration files with `$ref` and template overlays',
    long_description=long_desc,
    author='Kyle Lahnakoski',
    author_email='kyle@lahnakoski.com',
    url='https://github.com/klahnakoski/mo-json-config',
    license='MPL 2.0',
    packages=find_packages(".", lib_prefix=""),
    install_requires=["mo-dots>=2.18.18240","mo-files>=2.18.18240","mo-future>=2.18.18240","mo-json>=2.18.18240","mo-logs>=2.18.18240","requests"],
    include_package_data=True,
    zip_safe=False,
    classifiers=[  #https://pypi.python.org/pypi?%3Aaction=list_classifiers
        "Development Status :: 4 - Beta",
        "Topic :: Software Development :: Libraries",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)",
    ]
)
