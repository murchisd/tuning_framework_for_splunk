# Copyright 2018 Splunk Inc. All rights reserved.

# Python Standard Libraries
import re


class NoSectionError(Exception):
    """ Exception raised when a specified section is not found. """


class NoOptionError(Exception):
    """ Exception raised when a specified option is not found in the specified section. """


class DuplicateSectionError(Exception):
    """ Exception raised if add_section() is called with the name of a section that is already present. """


class ConfigurationSetting(object):

    def __init__(self, name, value, header=None, lineno=None):
        self.name = name
        self.value = value
        self.header = [] if header is None else header
        self.lineno = lineno


class ConfigurationSection(object):

    def __init__(self, name, header=None, lineno=None):
        self.name = name
        self.header = [] if header is None else header
        self.lineno = lineno
        self.options = dict()

    def add_option(self, name, value, header=None, lineno=None):
        self.options[name] = ConfigurationSetting(name, value, header=header,
                                                  lineno=lineno)

    def has_option(self, optname):
        #Update for python3
        #return self.options.has_key(optname)
        return optname in self.options 

    def has_setting_with_pattern(self, setting_key_regex_pattern):
        setting_key_regex_object = re.compile(setting_key_regex_pattern,
                                              re.IGNORECASE)
        for key, value in self.options.iteritems():
            if re.search(setting_key_regex_object, key):
                return True
        return False

    def get_option(self, optname):
        #Update for python3
        #if self.options.has_key(optname):
        if optname in self.options:
            return self.options[optname]
        else:
            error_output = ("No option '{}' exists in section '{}'"
                            ).format(optname, self.name)
            raise NoOptionError(error_output)

    def settings(self):
        for key, value in self.options.iteritems():
            yield self.options[key]

    def settings_with_key_pattern(self, setting_key_regex_pattern):
        setting_key_regex_object = re.compile(setting_key_regex_pattern,
                                              re.IGNORECASE)
        for key, value in self.options.iteritems():
            if re.search(setting_key_regex_object, key):
                yield value

    def items(self):
        #Updated for python3 no iteritems
        #return [(property_name, configuration_setting.value, configuration_setting.lineno)
        #        for (property_name, configuration_setting)
        #        in self.options.iteritems()]
        return [(property_name, configuration_setting.value, configuration_setting.lineno)
                for (property_name, configuration_setting)
                in self.options.items()]


class ConfigurationFile(object):

    def __init__(self):
        self.headers = []
        self.sects = dict()
        self.errors = []

    def set_main_headers(self, header):
        self.headers = header

    def add_error(self, error, lineno, section):
        self.errors.append((error, lineno, section))

    def get(self, sectionname, key):
        if self.has_section(sectionname):
            option = self.sects[sectionname].get_option(key)
            if option != None:
                return option.value
            else:
                error_output = ("The option does not exist in the section "
                                " searched. Section: {}"
                                " Option: '{}'").format(key, sectionname)
                raise NoOptionError(error_output)
        else:
            raise NoSectionError("No section '{}' exists".format(sectionname))

    def add_section(self, sectionname, header=None, lineno=None):
        section = ConfigurationSection(sectionname, header=header, lineno=lineno)
        self.sects[sectionname] = section
        return section

    def has_option(self, sectionname, key):
        return (self.has_section(sectionname) and
                self.get_section(sectionname).has_option(key))

    def has_section(self, sectionname):
        #Updated for python 3
        return sectionname in self.sects
        #return self.sects.has_key(sectionname)

    def get_section(self, sectionname):
        #Updated for python 3
        #if self.sects.has_key(sectionname):
        if sectionname in self.sects:
            return self.sects[sectionname]
        else:
            raise NoSectionError('No such section: {}'.format(sectionname))

    def section_names(self):
        return self.sects.keys()

    def sections(self):
        for key, value in self.sects.iteritems():
            yield value

    # Returns only sections that have a property that matches a regex pattern
    def sections_with_setting_key_pattern(self, setting_key_regex_pattern):
        setting_key_regex_object = re.compile(setting_key_regex_pattern,
                                              re.IGNORECASE)
        for key, value in self.sects.iteritems():
            for setting in value.settings():
                if re.search(setting_key_regex_object, setting.name):
                    yield value

    def items(self, sectionname):
        return self.get_section(sectionname).items()

    def build_lookup(self):
        """Build a dictionary from a config file where { sect => [options ...] }."""
        return {sect: [option for option in self.sects[sect].options] for sect in self.sects}