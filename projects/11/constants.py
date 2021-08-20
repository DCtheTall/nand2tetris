"""
Jack Compiler
=============
Constants module
----------------
This file contains constants used throughout the compiler.

"""


KEYWORDS = {'class', 'constructor', 'function', 'method', 'field', 'static',
            'var', 'int', 'char', 'boolean', 'bool', 'void', 'true', 'false',
            'null', 'this', 'let', 'do', 'if', 'else', 'while', 'return'}

SYMBOLS = {'{', '}', '(', ')', '[', ']', '.', ',', ';', '+', '-', '*', '/',
           '&', '|', '<', '>', '=', '~'}

WHITESPACE = {' ', '\t', '\r'}

BINARY_OPS = {'+', '-', '*', '/', '&', '|', '<', '>', '='}

UNARY_OPS = {'-', '~'}

KEYWORD_CONSTANTS = {'true', 'false', 'null', 'this'}
