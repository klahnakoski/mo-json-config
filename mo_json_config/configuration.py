import re

from mo_dots import is_data, to_data, join_field, Data
from mo_dots.datas import register_data
from mo_logs.strings import strip, wordify


class Configuration:

    def __init__(self, lookup):
        self.lookup = to_data(lookup)

    def __ior__(self, more_config):
        if is_data(more_config):
            for path, value in to_data(more_config).leaves():
                clean_path = join_field(wordify(path))
                self.lookup[clean_path]=value

    def __getattr__(self, item):
        clean_path = join_field(wordify(item))
        value = self.lookup[clean_path]
        if is_data(value):
            return Configuration(value)
        return value

    __getitem__ = __getattr__


register_data(Configuration)
