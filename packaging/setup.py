# encoding: utf-8
# THIS FILE IS AUTOGENERATED!
from setuptools import setup
setup(
    author='Kyle Lahnakoski',
    author_email='kyle@lahnakoski.com',
    classifiers=["Development Status :: 4 - Beta","Topic :: Software Development :: Libraries","Topic :: Software Development :: Libraries :: Python Modules","Programming Language :: Python :: 3.8","Programming Language :: Python :: 3.9","Programming Language :: Python :: 3.10","License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)","Programming Language :: Python :: 3.11","Programming Language :: Python :: 3.12"],
    description='More JSON Configuration! JSON configuration files with `$ref` and template overlays',
    extras_require={"tests":["mo-testing","keyring","boto3","moto","pyyaml"]},
    install_requires=["hjson","mo-dots==9.502.24024","mo-files==6.505.24024","mo-future==7.476.24007","mo-json==6.505.24024","mo-logs==8.503.24024","requests"],
    license='MPL 2.0',
    long_description='# More JSON Configuration!\n\n[![PyPI Latest Release](https://img.shields.io/pypi/v/mo-json-config.svg)](https://pypi.org/project/mo-json-config/)\n[![Build Status](https://app.travis-ci.com/klahnakoski/mo-json-config.svg?branch=master)](https://travis-ci.com/github/klahnakoski/mo-json-config)\n[![Coverage Status](https://coveralls.io/repos/github/klahnakoski/mo-json-config/badge.svg?branch=master)](https://coveralls.io/github/klahnakoski/mo-json-config?branch=master)\n\nA JSON template format intended for configuration files.\n\n## Motivation\n\nThis module reads JSON files and expands references found within. It is much like the IETF\'s  [JSON Reference](https://tools.ietf.org/html/draft-pbryan-zyp-json-ref-03) specification, but with the following differences:\n\n1. This module uses the dot (`.`) as a path separator in the URL fragment. For example, an absolute reference looks like `{"$ref": "#message.type.name"}`, and a relative reference looks like `{"$ref": "#..type.name"}`.   This syntax better matches that used by Javascript.\n2. The properties found in a `$ref` object are not ignored. Rather, they are to *override* the referenced object properties. This allows you to reference a default document, and replace the particular properties as needed. *more below*\n3. References can accept URL parameters: JSON is treated like a string template for more sophisticated value replacement. *see below*\n4. You can reference files and environment variables in addition to general URLs.\n\n## Quick guide\n\nLoad your configuration file:\n\n```python\nimport mo_json_config\n\nconfig = mo_json_config.get("file://my_config.json")\n```\n\nYou may use the global `configuration` object for case-insensitive lookup:\n\n\n```python\nfrom mo_json_config import configuration\n\n# use |= operator to add more configuration\nconfiguration |= {"some":{"deep":"value"}}\n\nassert configuration.someDeep == "value"\n\n```\n\n\n\n\n## Schemes\n\nThis module can load configuration from a number of sources, and you can access them via URI scheme.  Beyond the common `file` and `http` schemes, there are\n\n\n### Environment Variables\n\nUse the `env` scheme for accessing environment variables:\n\n    {\n        "host": "mail.example.com",\n        "username": "ekyle",\n        "password": {"$ref": "env://MAIL_PASSWORD"}\n    }\n\n\n### Keystore Values\n\nThe [keyring](https://pypi.org/project/keyring/) library can be used with the `keyring` scheme:\n \n    {\n        "host": "mail.example.com",\n        "username": "ekyle",\n        "password": {"$ref": "keyring://ekyle@mail.example.com"}\n    }\n\nThe host is in `<username>@<server_name>` format; invoking `keyring.get_password(server_name, username)`.  You may also set the username as a parameter:\n\n\n    {\n        "host": "mail.example.com",\n        "username": "ekyle",\n        "password": {"$ref": "keyring://mail.example.com?username=ekyle"}\n    }\n\n> Be sure to `pip install keyring` to use keyring\n\n\n### AWS SSM\n\nThe `ssm` scheme can be used to read from the AWS parameter store.  Here is an example that will read all parameters that start with "/configuration" and adds them to the global configuration object:\n\n```python\nfrom mo_json_config import get, configuration\n\nconfiguration |= get("ssm:///configuration")\n```\n  \n\n## Using references in config files\n\nThe `$ref` property is special. Its value is interpreted as a URL pointing to more JSON\n\n\n### Absolute Internal Reference\n\nThe simplest form of URL is an absolute reference to a node in the same\ndocument:\n\n\n    {\n        "message": "Hello world",\n        "repeat": {"$ref": "#message"}\n    }\n\n\nThe reference must start with `#`, and the object with the `$ref` is replaced\nwith the value it points to:\n\n\n    {\n        "message": "Hello world",\n        "repeat": "Hello world"\n    }\n\n\n### Relative Internal References\n\nReferences that start with dot (`.`) are relative, with each additional dot\nreferring to successive parents.   In this case the `..` refers to the\nref-object\'s parent, and expands just like the previous example:\n\n\n    {\n        "message": "Hello world",\n        "repeat": {"$ref": "#..message"}\n    }\n\n\n### File References\n\nConfiguration is often stored on the local file system. You can in-line the\nJSON found in a file by using the `file://` scheme:\n\nIt is good practice to store sensitive data in a secure place...\n\n\n    {# LOCATED IN C:\\users\\kyle\\password.json\n        "host": "database.example.com",\n        "username": "kyle",\n        "password": "pass123"\n    }\n\n...and then refer to it in your configuration file:\n\n\n    {\n        "host": "example.com",\n        "port": "8080",\n        "$ref": "file:///C:/users/kyle/password.json"\n    }\n\n\nwhich will be expanded at run-time to:\n\n\n    {\n        "host": "example.com",\n        "port": "8080",\n        "username": "kyle",\n        "password": "pass123"\n    }\n\n\nPlease notice the triple slash (`///`) is referring to an absolute file\nreference.\n\n### References To Objects\n\nRef-objects that point to other objects (dicts) are not replaced completely,\nbut rather are merged with the target; with the ref-object\nproperties taking precedence.   This is seen in the example above: The "host"\nproperty is not overwritten by the target\'s.\n\n### Relative File Reference\n\nHere is the same, using a relative file reference; which is relative to the\nfile that contains this JSON\n\n\n    {#LOCATED IN C:\\users\\kyle\\dev-debug.json\n        "host": "example.com",\n        "port": "8080",\n        "$ref": "file://password.json"\n    }\n    \n\n### Home Directory Reference\n\nYou may also use the tilde (`~`) to refer to the current user\'s home directory.\nHere is the same again, but this example can be anywhere in the file system.\n\n\n    {\n        "host": "example.com",\n        "port": "8080",\n        "$ref": "file://~/password.json"\n    }\n\n\n### HTTP Reference\n\nConfiguration can be stored remotely, especially in the case of larger\nconfigurations which are too unwieldy to inline:\n\n\n    {\n        "schema":{"$ref": "https://example.com/sources/my_db.json"}\n    }\n\n\n### Scheme-Relative Reference\n\nYou are also able to leave the scheme off, so that whole constellations of\nconfiguration files can refer to each other no matter if they are on the local\nfile system, or remote:\n\n\n    {# LOCATED AT SOMEWHERE AT http://example.com\n        "schema":{"$ref": "///sources/my_db.json"}\n    }\n\n\nAnd, of course, relative references are also allowed:\n\n\n    {# LOCATED AT http://example.com/sources/dev-debug.json\n        "schema":{"$ref": "//sources/my_db.json"}\n    }\n\n\n### Fragment Reference\n\nSome remote configuration files are quite large...\n\n    {# LOCATED IN C:\\users\\kyle\\password.json\n        "database":{\n            "username": "kyle",\n            "password": "pass123"\n        },\n        "email":{\n            "username": "ekyle",\n            "password": "pass123"\n        }\n    }\n\n... and you only need one fragment. For this use the hash (`#`) followed by\nthe dot-delimited path into the document:\n\n    {\n        "host": "mail.example.com",\n        "username": "ekyle",\n        "password": {"$ref": "//~/password.json#email.password"}\n    }\n\n### Parameters Reference\n\nYou can reference the variables found in `$ref` URL by using the `param` scheme. For example, the following JSON document demands that it be provided with a `password` parameter:  \n\n    { # LOCATED AT http://example.com/machine_config.json\n        "host": "mail.example.com",\n        "username": "ekyle",\n        "password": {"$ref": "param:///password"}\n    }\n\n> The `param` scheme only accepts dot-delimited paths.\n\nThe above parametric JSON can be expanded with a $ref\n\n\t{"config": {\n\t\t"$ref": "http://example.com/machine_config.json?password=pass123"\n\t}}\n\nexpands to \n\n    {"config": {\n        "host": "mail.example.com",\n        "username": "ekyle",\n        "password": "pass123"\n    }}\n\nURL parameters and `$ref` properties can conflict. Let\'s consider \n\n\t{"config": {\n\t\t"$ref": "http://example.com/machine_config.json?password=pass123",\n\t\t"password": "123456"\n\t}}\n\nthe URL paramters are used to expand the given document, **then** the `$ref` properties override the contents of the document:\n\n    {"config": {\n        "host": "mail.example.com",\n        "username": "ekyle",\n        "password": "123456"\n    }}\n\n\n## Comments\n\nEnd-of-line Comments are allowed, using either `#` or `//` prefix:\n\n```\n    "key1": "value1",  //Comment 1\n```\n\n```\n    "key1": "value1",  # Comment 1\n```\n\nMultiline comments are also allowed, using either Python\'s triple-quotes\n(`""" ... """`) or Javascript\'s block quotes `/*...*/`\n\n```\n{\n    "key1": /* Comment 1 */ "value1",\n}\n```\n\n```\n    "key1": """Comment 1""" "value1",\n```\n\n\n## Parameterized JSON\n\nThe `param` scheme is a good way to set property values in a document, but sometimes that is not enough.  Sometimes you want to parameterize property names, or change the document structure in unconventional ways. For these cases, JSON documents are allowed named parameters at the unicode level. Parameters are surrounded by moustaches `{{.}}`:\n\n```javascript\n{//above_example.json\n    {{var_name}}: "value"\n}\n```\n\nParameter replacement is performed on the unicode text before being interpreted by the JSON parser. It is your responsibility to ensure the parameter replacement will result in valid JSON.\n\nYou pass the parameters by including them as URL parameters:\n\n\t{"$ref": "//~/above_example.json?var_name=%22hello%22"}\n\nWhich will expand to\n\n    {\n        "hello": "value"\n    }\n\nThe pipe (`|`) symbol can be used to perform some common conversions\n\n\n    {\n        {{var_name|quote}}: "value"\n    }\n\nThe `quote` transformation will deal with quoting, so ...\n\n\t{"$ref": "//~/above_example.json?var_name=hello"}\n\n... expands to the same:\n\n    {\n        "hello": "value"\n    }\n\nPlease see [`expand_template()` in the `strings` module](https://github.com/klahnakoski/mo-logs/blob/dev/mo_logs/strings.py) for more on the parameter replacement, and transformations available\n\n',
    long_description_content_type='text/markdown',
    name='mo-json-config',
    packages=["mo_json_config"],
    url='https://github.com/klahnakoski/mo-json-config',
    version='4.505.24024'
)