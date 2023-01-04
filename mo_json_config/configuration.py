from mo_dots import is_data, to_data, join_field, leaves_to_data
from mo_dots.datas import register_data
from mo_logs import logger
from mo_logs.strings import wordify


class Configuration:

    def __init__(self, config):
        if not is_data(config):
            logger.error("Expecting data, not {{config}}", config=config)
        self.lookup = leaves_to_data({join_field(wordify(path)): value for path, value in to_data(config).leaves()})

    def __iadd__(self, other):
        """
        RECURSIVE ACCUMULATION OF PROPERTIES
        """
        self.lookup += Configuration(other).lookup
        return self

    def __ior__(self, other):
        """
        RECURSIVE COALESCE OF PROPERTIES
        """
        self.lookup |= Configuration(other).lookup
        return self

    def __getattr__(self, item):
        clean_path = join_field(wordify(item))
        value = self.lookup[clean_path]
        if is_data(value):
            return Configuration(value)
        return value

    __getitem__ = __getattr__


register_data(Configuration)
