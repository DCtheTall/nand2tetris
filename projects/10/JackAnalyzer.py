"""
Jack Syntax Analyzer
--------------------
This program contains a Jack programming language syntax analyzer.

It parses a directory of Jack files and outputs XML files which represent
the Jack programs' abstract syntax tree.

Parser:
-   Reads the input directory for .jack files.
-   For each file it tokenizes the source code.
-   For each tokenized file, it outputs the corresponding <name>T.xml file.
-   For each list of tokens it constructs the abstract syntax tree using
    the parsing rules from the class.
-   It outputs each abstract syntax tree as a .xml file.

"""


import os
import sys

from typing import List, NamedTuple, Tuple


KEYWORDS = {'class', 'constructor', 'function', 'method', 'field', 'static',
            'var', 'int', 'char', 'boolean', 'bool', 'void', 'true', 'false',
            'null', 'this', 'let', 'do', 'if', 'else', 'while', 'return'}

SYMBOLS = {'{', '}', '(', ')', '[', ']', '.', ',', ';', '+', '-', '*', '/',
           '&', '|', '<', '>', '=', '~'}

WHITESPACE = {' ', '\t', '\r'}


class InvalidInputError(Exception):
  """Custom exception type for when users input invalid command line arguments."""

  def __init__(self, msg: str):
    super(InvalidInputError, self).__init__(
        msg if msg else 'Must be called `python JackAnalyzer.py '
                        'path/to/input/dir/')


def ParseJackFilePathsFromArguments() -> List[str]:
  """Parse command line arguments and return the paths to all the Jack files to analyze."""
  if len(sys.argv) != 2:
    raise InvalidInputError()
  inp_path = sys.argv[1]
  if not os.path.isdir(inp_path):
    raise InvalidInputError()
  jack_filenames = [fname for fname in os.listdir(inp_path)
                          if fname.endswith('.jack')]
  if 'Main.jack' not in jack_filenames:
    raise InvalidInputError('Directory must contain a Main.jack file')
  return [os.path.join(inp_path, fname) for fname in jack_filenames]


class Token(object):
  """Base token class, all other tokens inherit from this class."""
  def __init__(self, value):
    self.value = value

  def __eq__(self, other) -> bool:
    return ((self.__class__, self.value) ==
            (other.__class__, other.value))

  def TagName(self) -> str:
    """Virtual method that gets the Token's XML tag name."""
    raise NotImplementedError('TagName not implemented')

  def Value(self) -> str:
    """Value property formatted for XML"""
    if not isinstance(self.value, str):
      return self.value
    return self.value.replace('<', '&lt;').replace('>', '&gt;')

class KeywordToken(Token):
  def TagName(self) -> str:
    return 'keyword'

class SymbolToken(Token):
  def TagName(self) -> str:
    return 'symbol'

class IntegerConstantToken(Token):
  def TagName(self) -> str:
    return 'integerConstant'

class StringConstantToken(Token):
  def TagName(self) -> str:
    return 'stringConstant'

class IdentifierToken(Token):
  def TagName(self) -> str:
    return 'identifier'


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


class XMLTag:
  """Class encapsulates building an XML tag string"""
  def __init__(self, tag_name: str):
    self.tag_name = tag_name
    self.text = ''
    self.children = []

  def __str__(self):
    if not self.children:
      return f'<{self.tag_name}> {self.text} </{self.tag_name}>'
    lines = [f'<{self.tag_name}>']
    for child in self.children:
      child_lines = str(child.xml).split('\n')
      indent = ' ' * child.indent
      for i, line in enumerate(child_lines):
        child_lines[i] = f'{indent}{line}'
      lines.extend(child_lines)
    lines.append(f'</{self.tag_name}>')
    return '\n'.join(lines)

  def Text(self, text: str):
    self.text = text

  def AddChild(self, child, indent=0):
    self.children.append(XMLChild(xml=child, indent=indent))


class XMLChild(NamedTuple):
  xml: XMLTag
  indent: int


def TokensToXMLString(tokens: List[Token]) -> str:
  """Generate an XML string from a list of tokens."""
  xml = XMLTag('tokens')
  for token in tokens:
    child = XMLTag(token.TagName())
    child.Text(token.Value())
    xml.AddChild(child)
  result = str(xml)
  return result + '\n'


class SyntaxTreeNode:
  """Base class for a node in the abstract syntax tree."""
  def TagName(self):
    raise NotImplementedError('TagName not implemented')


class TerminalNode(SyntaxTreeNode):
  def __init__(self, token: Token):
    super(TerminalNode, self).__init__()

# Terminal nodes inherit from token classes for TagName and Value
class KeywordNode(KeywordToken, TerminalNode):
  pass

class SymbolNode(SymbolToken, TerminalNode):
  pass

class IntegerConstantNode(IntegerConstantToken, TerminalNode):
  pass

class StringConstantNode(StringConstantToken, TerminalNode):
  pass

class IdentifierNode(IdentifierToken, TerminalNode):
  pass


class NonTerminalNode(SyntaxTreeNode):
  def __init__(self):
    super(NonTerminalNode, self).__init__()
    self.children = []

  def AddChild(self, child: SyntaxTreeNode):
    """Add a new child to the subtree."""
    self.children.append(child)

  def AddChildren(self, *children: List[SyntaxTreeNode]):
    """Add a list of children to the subtree."""
    self.children.extend(children)

class ClassNode(NonTerminalNode):
  def TagName(self):
    return 'class'


class ClassVarDecNode(NonTerminalNode):
  def TagName(self):
    return 'classVarDec'


class SubroutineDecNode(NonTerminalNode):
  def TagName(self):
    return 'subroutineDec'


def CompileClass(tokens: List[Token]) -> ClassNode:
  """Compile a class statement from tokens."""
  if (tokens[0] != KeywordToken('class')
      or (not isinstance(tokens[1], IdentifierToken))
      or tokens[2] != SymbolToken('{')
      or tokens[-1] != SymbolToken('}')):
    raise InvalidInputError('Invalid class')
  node = ClassNode()
  node.AddChildren(
      KeywordNode('class'), IdentifierNode(tokens[1].Value()), SymbolNode('{'))

  tokens = tokens[3:-1]
  nodes, i = CompileClassVarDecs(tokens)
  node.AddChildren(*nodes)

  tokens = tokens[i:]
  node.AddChildren(*CompileSubroutines(tokens))

  node.AddChild(SymbolNode('}'))
  return node


def CompileClassVarDecs(
    tokens: List[Token]) -> Tuple[List[ClassVarDecNode], int]:
  """Compile the class variable declarations."""
  i = 0
  nodes = []
  syntax_err = SyntaxError('Invalid class variable declaration')
  while (tokens[i] == KeywordToken('static')
         or tokens[i] == KeywordToken('field')):
    node = ClassVarDecNode()
    
    if tokens[i] == KeywordToken('static'):
      node.AddChild(KeywordNode('static'))
    else:
      node.AddChild(KeywordNode('field'))
    i += 1

    node.AddChild(ParseType(tokens[i]))
    i += 1

    if not isinstance(tokens[i], IdentifierToken):
      raise syntax_err
    node.AddChild(IdentifierNode(tokens[i].Value()))
    i += 1

    while tokens[i] == SymbolToken(','):
      node.AddChild(SymbolNode(','))
      i += 1
      if not isinstance(tokens[i], IdentifierToken):
        raise syntax_err
      node.AddChild(IdentifierNode(tokens[i].Value()))
      i += 1

    if tokens[i] != SymbolToken(';'):
      raise syntax_err
    node.AddChild(SymbolNode(';'))
    i += 1

    nodes.append(node)
  return nodes, i


def ParseType(token: Token):
  if isinstance(token, KeywordToken):
    return KeywordNode(token.Value())
  if isinstance(token, IdentifierToken):
    return IdentifierNode(token.Value())
  raise SyntaxError()


def CompileSubroutines(tokens: List[Token]) -> List[SubroutineDecNode]:
  """Compile subroutine declarations"""
  nodes = []
  i = 0
  syntax_err = SyntaxError('Invalid subroutine declaration')
  while i < len(tokens):
    node = SubroutineDecNode()

    if not (tokens[i] == KeywordToken('constructor')
            or tokens[i] == KeywordToken('method')
            or tokens[i] == KeywordToken('function')):
      raise syntax_err
    node.AddChild(KeywordNode(tokens[i].Value()))
    i += 1

    if tokens[i] == KeywordToken('void'):
      node.AddChild(KeywordNode('void'))
    else:
      node.AddChild(ParseType(tokens[i]))
    i += 1

    if not isinstance(tokens[i], IdentifierToken):
      raise syntax_err
    node.AddChild(IdentifierNode(tokens[i].Value()))
    i += 1

    if tokens[i] != SymbolToken('('):
      raise syntax_err
    node.AddChild(SymbolNode('('))
    i += 1

    # TODO parse parameter list
    print(tokens[i].Value())

    nodes.append(node)
  return nodes


def main():
  """Main function"""
  for file_path in ParseJackFilePathsFromArguments():
    print(file_path)
    tokens = Tokenize(file_path)
    _ = TokensToXMLString(tokens)
    # TODO write token XML to file
    syntax_tree = CompileClass(tokens)


if __name__ == '__main__':
  main()
