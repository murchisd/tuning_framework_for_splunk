"""The configuration parsing logic for Splunk .conf files."""

# Copyright 2018 Splunk Inc. All rights reserved.

# Python Standard Libraries
import re
#2021-09-01 - DM Added for Python 3
import io
# Third-Party Libraries
import chardet
# Custom Libraries
# N/A

class InvalidSectionError(Exception):
    """ Exception raised when a invalid section is found. """


def join_lines(iterator):
    currentLine = ""
    lineno = 0
    # the new lines and carriage returns are stripped for iterators, otherwise
    # the regex will be flagged and the confparse will fail
    error = None

    # ACD-1714, Sometimes the customer's file is not standard UTF-8 encoded file (e.g. UTF-8-SIG)
    # Updated to use io.IOBase - no file object type in python3
    # Removed section until can update for Python3
    #if isinstance(iterator, io.IOBase):
    #    encoding = chardet.detect(iterator.read(32))['encoding']
    #    iterator.seek(0)
    #   iterator = (line.decode(encoding, errors='ignore') for line in iterator)

    for line in (line.rstrip("\r\n") for line in iterator):
        lineno += 1
        if re.search("\\\\\\s*$", line):
            if line != line.rstrip():
                error = "Continuation with trailing whitespace"
            newline = line[:-1] + "\n"
            currentLine += newline
        else:
            yield (currentLine + line, lineno, error)
            error = None  # Reset on each yield
            currentLine = ""


def configuration_lexer(iterator):
    try:
        for item, lineno, error in join_lines(iterator):
            if item == '' or item.isspace():
                yield ('WHITESPACE', '', lineno, error)
            elif re.match("^\\s*[#;]", item):
                yield ('COMMENT', item.lstrip(), lineno, error)
            elif re.match("^\\s*\\[", item):
                start = item.index('[')
                end = item.rindex(']', start)
                yield ('STANZA', item[start + 1:end], lineno, error)
            elif '=' in item:
                key, value = item.split('=', 1)
                yield ('KEYVAL', (key.strip(), value.strip()), lineno, error)
            else:
                yield ('RANDSTRING', item, lineno, error)
    except ValueError:
        raise InvalidSectionError('Invalid item: {}, line: {}'.format(item, lineno))
    except Exception:
        # re-raise other errors, it might be code error that need to further investigation
        raise


def specification_lexer(iterator):
    for item, lineno, error in join_lines(iterator):
        if item == '' or item.isspace():
            yield ('WHITESPACE', '', lineno, error)
        elif re.match("^\\s*[#;*]", item):
            yield ('COMMENT', item.lstrip(), lineno, error)
        elif re.match("^\\s*\\[", item):
            start = item.index('[')
            end = item.index(']', start)
            yield ('STANZA', item[start + 1:end], lineno, error)
        elif '=' in item:
            key, value = item.split('=', 1)
            yield ('KEYVAL', (key.strip(), value.strip()), lineno, error)
        else:
            yield ('RANDSTRING', item, lineno, error)


def parse(iterator_or_string, configuration_file, lexer):
    if isinstance(iterator_or_string, str):
        return parse(iterator_or_string.split('\n'), configuration_file, lexer)

    headers = []
    current_section = None

    for type, item, lineno, error in lexer(iterator_or_string):
        if type in ['WHITESPACE', 'COMMENT', 'RANDSTRING']:
            # Not propogating errors on comments.
            headers.append(item)
        if(type in ['STANZA', 'KEYVAL'] and
                current_section == None):
            configuration_file.set_main_headers(headers)
            headers = []
        if type == 'STANZA':
            if configuration_file.has_section(item):
                configuration_file.add_error("Duplicate stanza", lineno, item)
            current_section = configuration_file.add_section(item,
                                                             header=headers,
                                                             lineno=lineno)
            if error:
                configuration_file.add_error(error, lineno, item)
            headers = []
        if type == 'KEYVAL':
            if not(current_section):
                current_section = configuration_file.add_section('default',
                                                                 header=headers,
                                                                 lineno=lineno)
            if error:
                configuration_file.add_error(error,
                                             lineno,
                                             current_section.name)

            if current_section.has_option(item[0]):
                error_message = "Repeat item name '{}'".format(item[0])
                configuration_file.add_error(error_message,
                                             lineno,
                                             current_section.name)

            current_section.add_option(item[0], item[1], header=headers,
                                       lineno=lineno)
            headers = []

    return configuration_file