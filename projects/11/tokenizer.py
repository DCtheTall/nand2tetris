"""
Jack Compiler
=============
Tokenizer module
----------------
This file contains all the code for tokenizing Jack code.
This was originally implemented in project 10.

"""

import os

from typing import List

from constants import KEYWORDS, SYMBOLS, WHITESPACE


class InvalidInputError(Exception):
  """Custom exception type for when users input invalid command line arguments."""

  def __init__(self, msg: str):
    super(InvalidInputError, self).__init__(
        msg if msg else 'Must be called `python JackAnalyzer.py '
                        'path/to/input/dir/')


class Token(object):
  """Base token class, all other tokens inherit from this class."""
  def __init__(self, value):
    self.value = value

  def __eq__(self, other) -> bool:
    return ((self.__class__, self.value) ==
            (other.__class__, other.value))

  def Value(self) -> str:
    """Value property formatted for XML"""
    if not isinstance(self.value, str):
      return str(self.value)
    if self.value == '<':
      return '&lt;'
    if self.value == '>':
      return '&gt;'
    if self.value == '&':
      return '&amp;'
    return self.value

class KeywordToken(Token):
  pass

class SymbolToken(Token):
  pass

class IntegerConstantToken(Token):
  pass

class StringConstantToken(Token):
  pass

class IdentifierToken(Token):
  pass


def Tokenize(jack_file_path: str) -> List[Token]:
  """Tokenize the content of a .jack file path."""
  with open(jack_file_path, 'r') as f:
    jack_file_content = f.read()
  jack_file_content = RemoveMultilineComments(jack_file_content)
  jack_file_lines = RemoveSingleLineComments(jack_file_content.split('\n'))
  tokens = []
  for line in jack_file_lines:
    tokens.extend(TokenizeLine(line))
  if tokens[0] != KeywordToken('class'):
    raise SyntaxError('Expected class')
  if tokens[-1] != SymbolToken('}'):
    raise SyntaxError('Unexpected characters after }')
  return tokens


def RemoveMultilineComments(jack_file_content: str) -> str:
  """Strips away any multiline comments from the .jack file."""
  result = []
  while True:
    try:
      idx = jack_file_content.index('/*')
      result.append(jack_file_content[:idx])
    except ValueError:
      result.append(jack_file_content)
      break
    try:
      jack_file_content = jack_file_content[idx+2:]
      idx = jack_file_content.index('*/')
      jack_file_content = jack_file_content[idx+2:]
    except ValueError:
      raise SyntaxError('Expected */ before end of file')
  return ''.join(result)


def RemoveSingleLineComments(jack_file_lines: List[str]) -> List[str]:
  """Remove any single line comments and empty lines."""
  result = []
  for line in jack_file_lines:
    try:
      line = line[:line.index('//')]
      if line:
        result.append(line)
    except ValueError:
      result.append(line)
  return result


def TokenizeLine(line: str) -> List[Token]:
  """Tokenize a line of Jack code. Always non-empty."""
  i = 0
  cur = ''
  tokens = []
  while i < len(line):
    if line[i] in WHITESPACE:
      if cur:
        tokens.append(TokenizeString(cur))
        cur = ''
      i += 1
      continue
    if line[i] in SYMBOLS:
      if cur:
        tokens.append(TokenizeString(cur))
        cur = ''
      tokens.append(SymbolToken(line[i]))
      i += 1
      continue
    if line[i] == '"':
      if cur:
        raise SyntaxError('Unexpected characters before string')
      try:
        j = line[i+1:].index('"')
      except ValueError:
        raise SyntaxError('Expected string to end before line ends')
      tokens.append(StringConstantToken(line[i+1:i+1+j]))
      i += j + 2
      continue
    cur += line[i]
    i += 1
  return tokens


def TokenizeString(value: str) -> Token:
  """Tokenize the given string"""
  if not value:
    raise InvalidInputError('Expected non-empty string')
  if value in KEYWORDS:
    return KeywordToken(value)
  try:
    return IntegerConstantToken(int(value))
  except ValueError:
    pass
  try:
    int(value[0])
    raise SyntaxError('Identifiers cannot start with numbers')
  except ValueError:
    pass
  return IdentifierToken(value)


def TestTokenizer():
  example_jack_content = """
  class Main {
    function void main() {
      var int x;
      var int y;
      var int sum;
      let x = 2;
      let y = 3;
      let sum = x + y;
    }
  }
  """
  tmp_jack_file_path = '/tmp/Main.jack'
  with open(tmp_jack_file_path, 'w') as f:
    f.write(example_jack_content)
  
  tokens = Tokenize(tmp_jack_file_path)
  assert len(tokens) > 0
  assert all(isinstance(t, Token) for t in tokens)
  print('Test passed!')

  os.remove(tmp_jack_file_path)


if __name__ == '__main__':
  TestTokenizer()
