import os


class Config(object):
    """Simple environment variable based configuration object.
    Configuration key-value pairs can also be set directly, or
    read from a file using the class method ``Config.from_file()``.
    When variables are set directly, the system environment is not updated.

    Usage:
        >>> os.environ['MY_CONFIG_KEY'] = 'test value'
        >>> form pooldlib.config import Config
        >>> config = Config()
        >>> config.MY_CONFIG_KEY
        'test value'
        >>> config.my_config_key
        'test value'
        >>> config.another_config_key = 'another test value'
        >>> config.another_config_key
        'another test value'
    """

    def __getattr__(self, name):
        name = name.upper()
        attr = '_%s' % name
        try:
            return object.__getattribute__(self, attr)
        except AttributeError:
            pass
        value = os.environ.get(name)  # Default to None if the value is not defined
        #if not value:
        #    msg = 'Unknown configuration value: %s' % name
        #    raise ConfigurationError(msg)
        setattr(self, attr, value)
        return value

    def __setattr__(self, name, value):
        name = name.upper()
        attr = '_%s' % name
        object.__setattr__(self, attr, value)

    def update(self, dict):
        """Update stored configuration. Values set via the update method
        will take precedence over system environment variables.

        :param dict: Dictionary of key-value pairs to use in updating configuration.
        :type dict: dictionary
        """
        for (key, value) in dict.items():
            setattr(self, key, value)

    @classmethod
    def from_file(cls, file_path):
        """Read configuration from file. Currently all values are read
        in as strings. Configuration file should be in the format

            config_key = config_value

        Lines starting with ``#`` will be ignored.

        :param file_path: The system path at which the configuration file is located.
        :type file_path: string
        """
        with open(file_path, 'r') as fp:
            config = cls()
            for line in fp.readlines():
                if line.strip() and not line.startswith('#'):
                    key, value = line.split('=')
                    setattr(config, key.strip(), value.strip())
        return config
