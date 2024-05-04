# More JSON Configuration!

[![PyPI Latest Release](https://img.shields.io/pypi/v/mo-json-config.svg)](https://pypi.org/project/mo-json-config/)
[![Build Status](https://github.com/klahnakoski/mo-json-config/actions/workflows/build.yml/badge.svg?branch=master)](https://github.com/klahnakoski/mo-json-config/actions/workflows/build.yml)
[![Coverage Status](https://coveralls.io/repos/github/klahnakoski/mo-json-config/badge.svg?branch=dev)](https://coveralls.io/github/klahnakoski/mo-json-config?branch=dev)

A JSON template format intended for configuration files.

## Motivation

This module reads JSON files and expands references found within. It is much like the IETF's  [JSON Reference](https://tools.ietf.org/html/draft-pbryan-zyp-json-ref-03) specification, but with the following differences:

1. This module uses the dot (`.`) as a path separator in the URL fragment. For example, an absolute reference looks like `{"$ref": "#message.type.name"}`, and a relative reference looks like `{"$ref": "#..type.name"}`.   This syntax better matches that used by Javascript.
2. The properties found in a `$ref` object are not ignored. Rather, they are to *override* the referenced object properties. This allows you to reference a default document, and replace the particular properties as needed. *more below*
3. References can accept URL parameters: JSON is treated like a string template for more sophisticated value replacement. *see below*
4. You can reference 
   * http URLs
   * files
   * environment variables
   * keyring values
   * AWS SSM parameters

## Quick guide

Load your configuration file:

```python
import mo_json_config

config = mo_json_config.get("file://my_config.json")
```

You may use the global `configuration` object for case-insensitive lookup:


```python
from mo_json_config import configuration

# use |= operator to add more configuration
configuration |= {"some":{"deep":"value"}}

assert configuration.someDeep == "value"

```


## Schemes

This module can load configuration from a number of sources, and you can access them via URI scheme.  Beyond the common `file` and `https` schemes, there are


#### Environment Variables

Use the `env` scheme for accessing environment variables:

    {
        "host": "mail.example.com",
        "username": "ekyle",
        "password": {"$ref": "env://MAIL_PASSWORD"}
    }


#### Keystore Values

The [keyring](https://pypi.org/project/keyring/) library can be used with the `keyring` scheme:
 
    {
        "host": "mail.example.com",
        "username": "ekyle",
        "password": {"$ref": "keyring://ekyle@mail.example.com"}
    }

The host is in `<username>@<server_name>` format; invoking `keyring.get_password(server_name, username)`.  You may also set the username as a parameter:


    {
        "host": "mail.example.com",
        "username": "ekyle",
        "password": {"$ref": "keyring://mail.example.com?username=ekyle"}
    }

> Be sure to `pip install keyring` to use keyring


#### AWS SSM

The `ssm` scheme can be used to read from the AWS parameter store.  Here is an example that will read all parameters that start with "/configuration" and adds them to the global configuration object:

```python
from mo_json_config import get, configuration

configuration |= get("ssm:///configuration")
```
  
## String Template Expansion

Before going into the minutia of expanding `$ref` objects, let's look at simpler string template expansion:  Any string that contains a reference (of the form `{scheme://...}`) will have that reference replaced with the string it points to.  

Consider an example where we want to name a number of components with a common application name.  You may define them by using.  

    {
        "database_name": "{env://APP_NAME}-database"
        "queue_name": "{env://APP_NAME}-queue"
    }

If we assume

```
export APP_NAME=my-app-name
```

then the above JSON will expand to


    {
        "database_name": "my-app-name-database"
        "queue_name": "my-app-name-queue"
    }

These references can be used in the `$ref` object, as well, providing another level of indirection to the configuration file.


## Using references in config files

The `$ref` property is special. Its value is interpreted as a URL pointing to more JSON


### Absolute Internal Reference

The simplest form of URL is an absolute reference to a node in the same
document:


    {
        "message": "Hello world",
        "repeat": {"$ref": "#message"}
    }


The reference must start with `#`, and the object with the `$ref` is replaced
with the value it points to:


    {
        "message": "Hello world",
        "repeat": "Hello world"
    }


### Relative Internal References

References that start with dot (`.`) are relative, with each additional dot
referring to successive parents.   In this case the `..` refers to the
ref-object's parent, and expands just like the previous example:


    {
        "message": "Hello world",
        "repeat": {"$ref": "#..message"}
    }


### File References

Configuration is often stored on the local file system. You can in-line the
JSON found in a file by using the `file://` scheme:

It is good practice to store sensitive data in a secure place...


    {# LOCATED IN C:\users\kyle\password.json
        "host": "database.example.com",
        "username": "kyle",
        "password": "pass123"
    }

...and then refer to it in your configuration file:


    {
        "host": "example.com",
        "port": "8080",
        "$ref": "file:///C:/users/kyle/password.json"
    }


which will be expanded at run-time to:


    {
        "host": "example.com",
        "port": "8080",
        "username": "kyle",
        "password": "pass123"
    }


Please notice the triple slash (`///`) is referring to an absolute file
reference.

### References To Objects

Ref-objects that point to other objects (dicts) are not replaced completely,
but rather are merged with the target; with the ref-object
properties taking precedence.   This is seen in the example above: The "host"
property is not overwritten by the target's.

### Relative File Reference

Here is the same, using a relative file reference; which is relative to the
file that contains this JSON


    {#LOCATED IN C:\users\kyle\dev-debug.json
        "host": "example.com",
        "port": "8080",
        "$ref": "file://password.json"
    }
    

### Home Directory Reference

You may also use the tilde (`~`) to refer to the current user's home directory.
Here is the same again, but this example can be anywhere in the file system.


    {
        "host": "example.com",
        "port": "8080",
        "$ref": "file://~/password.json"
    }


### HTTP Reference

Configuration can be stored remotely, especially in the case of larger
configurations which are too unwieldy to inline:


    {
        "schema":{"$ref": "https://example.com/sources/my_db.json"}
    }


### Scheme-Relative Reference

You are also able to leave the scheme off, so that whole constellations of
configuration files can refer to each other no matter if they are on the local
file system, or remote:


    {# LOCATED AT SOMEWHERE AT http://example.com
        "schema":{"$ref": "///sources/my_db.json"}
    }


And, of course, relative references are also allowed:


    {# LOCATED AT http://example.com/sources/dev-debug.json
        "schema":{"$ref": "//sources/my_db.json"}
    }


### Fragment Reference

Some remote configuration files are quite large...

    {# LOCATED IN C:\users\kyle\password.json
        "database":{
            "username": "kyle",
            "password": "pass123"
        },
        "email":{
            "username": "ekyle",
            "password": "pass123"
        }
    }

... and you only need one fragment. For this use the hash (`#`) followed by
the dot-delimited path into the document:

    {
        "host": "mail.example.com",
        "username": "ekyle",
        "password": {"$ref": "//~/password.json#email.password"}
    }

### Parameters Reference

You can reference the variables found in `$ref` URL by using the `param` scheme. For example, the following JSON document demands that it be provided with a `password` parameter:  

    { # LOCATED AT http://example.com/machine_config.json
        "host": "mail.example.com",
        "username": "ekyle",
        "password": {"$ref": "param:///password"}
    }

> The `param` scheme only accepts dot-delimited paths.

The above parametric JSON can be expanded with a $ref

	{"config": {
		"$ref": "http://example.com/machine_config.json?password=pass123"
	}}

expands to 

    {"config": {
        "host": "mail.example.com",
        "username": "ekyle",
        "password": "pass123"
    }}

URL parameters and `$ref` properties can conflict. Let's consider 

	{"config": {
		"$ref": "http://example.com/machine_config.json?password=pass123",
		"password": "123456"
	}}

the URL paramters are used to expand the given document, **then** the `$ref` properties override the contents of the document:

    {"config": {
        "host": "mail.example.com",
        "username": "ekyle",
        "password": "123456"
    }}


## Comments

End-of-line Comments are allowed, using either `#` or `//` prefix:

```
    "key1": "value1",  //Comment 1
```

```
    "key1": "value1",  # Comment 1
```

Multiline comments are also allowed, using either Python's triple-quotes
(`""" ... """`) or Javascript's block quotes `/*...*/`

```
{
    "key1": /* Comment 1 */ "value1",
}
```

```
    "key1": """Comment 1""" "value1",
```


## Parameterized JSON

The `param` scheme is a good way to set property values in a document, but sometimes that is not enough.  Sometimes you want to parameterize property names, or change the document structure in unconventional ways. For these cases, JSON documents are allowed named parameters at the unicode level. Parameters are surrounded by moustaches `{{.}}`:

```javascript
{//above_example.json
    {var_name}: "value"
}
```

Parameter replacement is performed on the unicode text before being interpreted by the JSON parser. It is your responsibility to ensure the parameter replacement will result in valid JSON.

You pass the parameters by including them as URL parameters:

	{"$ref": "//~/above_example.json?var_name=%22hello%22"}

Which will expand to

    {
        "hello": "value"
    }

The pipe (`|`) symbol can be used to perform some common conversions


    {
        {{var_name|quote}}: "value"
    }

The `quote` transformation will deal with quoting, so ...

	{"$ref": "//~/above_example.json?var_name=hello"}

... expands to the same:

    {
        "hello": "value"
    }

Please see [`expand_template()` in the `strings` module](https://github.com/klahnakoski/mo-logs/blob/dev/mo_logs/strings.py) for more on the parameter replacement, and transformations available

