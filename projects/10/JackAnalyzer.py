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

BINARY_OPS = {'+', '-', '*', '/', '&', '|', '<', '>', '='}

UNARY_OPS = {'-', '~'}

KEYWORD_CONSTANTS = {'true', 'false', 'null', 'this'}


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
      return str(self.value)
    if self.value == '<':
      return '&lt;'
    if self.value == '>':
      return '&gt;'
    if self.value == '&':
      return '&amp;'
    return self.value

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
      if self.text:
        return f'<{self.tag_name}> {self.text} </{self.tag_name}>'
      else:
        return f'<{self.tag_name}>\n</{self.tag_name}>'
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
  

def WriteTokensXML(jack_file_path: str, tokens: List[Token]) -> str:
  """Write the tokenized .jack file into a .xml file."""
  out_dir, jack_filename = os.path.split(jack_file_path)
  out_path = os.path.join(out_dir, jack_filename.replace('.jack', 'T.xml'))
  with open(out_path, 'w') as f:
    f.write(TokensToXMLString(tokens))


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
  pass

# Terminal nodes inherit from Token classes for TagName and Value
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

class ParameterListNode(NonTerminalNode):
  def TagName(self):
    return 'parameterList'

class SubroutineBodyNode(NonTerminalNode):
  def TagName(self):
    return 'subroutineBody'

class VarDecNode(NonTerminalNode):
  def TagName(self):
    return 'varDec'

class StatementsNode(NonTerminalNode):
  def TagName(self):
    return 'statements'

class LetStatementNode(NonTerminalNode):
  def TagName(self):
    return 'letStatement'

class DoStatementNode(NonTerminalNode):
  def TagName(self):
    return 'doStatement'

class ReturnStatementNode(NonTerminalNode):
  def TagName(self):
    return 'returnStatement'

class WhileStatementNode(NonTerminalNode):
  def TagName(self):
    return 'whileStatement'

class IfStatementNode(NonTerminalNode):
  def TagName(self):
    return 'ifStatement'

class ExpressionNode(NonTerminalNode):
  def TagName(self):
    return 'expression'

class TermNode(NonTerminalNode):
  def TagName(self):
    return 'term'

class ExpressionListNode(NonTerminalNode):
  def TagName(self):
    return 'expressionList'


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
  while (tokens[i] == KeywordToken('static')
         or tokens[i] == KeywordToken('field')):
    node = ClassVarDecNode()
    node.AddChild(KeywordNode(tokens[i].Value()))
    i += 1
    node.AddChild(ParseType(tokens[i]))
    i += 1

    children, i = ParseVarNames(tokens, i)
    node.AddChildren(*children)

    nodes.append(node)
  return nodes, i


def ParseVarNames(
    tokens: List[Token], i: int) -> Tuple[List[NonTerminalNode], int]:
  """Parse a single or multiple comma separated variable names of the same type."""
  nodes = []
  syntax_err = SyntaxError('Invalid variable name')
  if not isinstance(tokens[i], IdentifierToken):
    raise syntax_err
  nodes.append(IdentifierNode(tokens[i].Value()))
  i += 1

  while tokens[i] == SymbolToken(','):
    nodes.append(SymbolNode(','))
    i += 1
    if not isinstance(tokens[i], IdentifierToken):
      raise syntax_err
    nodes.append(IdentifierNode(tokens[i].Value()))
    i += 1

  if tokens[i] != SymbolToken(';'):
    raise syntax_err
  nodes.append(SymbolNode(';'))
  i += 1
  return nodes, i


def ParseType(token: Token):
  """Parse a token used to indicate a variable's type."""
  if isinstance(token, KeywordToken):
    return KeywordNode(token.Value())
  if isinstance(token, IdentifierToken):
    return IdentifierNode(token.Value())
  raise SyntaxError('Invalid type')


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

    j = i + 1
    while tokens[j] != SymbolToken(')') and j < len(tokens):
      j += 1
    if j == len(tokens):
      raise syntax_err
    node.AddChild(ParseParameterList(tokens[i+1:j]))
    node.AddChild(SymbolNode(')'))
    i = j + 1

    child, i = CompileSubroutineBody(tokens, i)
    node.AddChild(child)

    nodes.append(node)
  return nodes


def ParseParameterList(tokens: List[Token]) -> ParameterListNode:
  """Parse a parameter list from the given tokens for a subroutine declaration.
  
  Tokens list should only contain tokens in the parameter list."""
  node = ParameterListNode()
  i = 0
  while i < len(tokens):
    node.AddChild(ParseType(tokens[i]))
    i += 1

    if not isinstance(tokens[i], IdentifierToken):
      raise SyntaxError('Invalid parameter list')
    node.AddChild(IdentifierNode(tokens[i].Value()))
    i += 1

    if i < len(tokens) and tokens[i] == SymbolToken(','):
      node.AddChild(SymbolNode(','))
      i += 1
  return node


def CompileSubroutineBody(
    tokens: List[Token], i: int) -> Tuple[SubroutineBodyNode, int]:
  """"""
  node = SubroutineBodyNode()

  if tokens[i] != SymbolToken('{'):
    raise SyntaxError('Invalid subroutine body')
  node.AddChild(SymbolNode('{'))
  i += 1

  nodes, i = CompileVarDecs(tokens, i)
  node.AddChildren(*nodes)

  child, i = CompileStatements(tokens, i)
  node.AddChild(child)
  
  if tokens[i] != SymbolToken('}'):
    raise SyntaxError('Invalid subroutine body')
  node.AddChild(SymbolNode('}'))
  i += 1

  return node, i


def CompileVarDecs(
    tokens: List[Token], i: int) -> Tuple[List[VarDecNode], int]:
  """Compile the variable declarations in a subroutine body."""
  nodes = []
  while tokens[i] == KeywordToken('var'):
    node = VarDecNode()
    node.AddChild(KeywordNode('var'))
    i += 1

    node.AddChild(ParseType(tokens[i]))
    i += 1

    children, i = ParseVarNames(tokens, i)
    node.AddChildren(*children)

    nodes.append(node)
  return nodes, i


def CompileStatements(
    tokens: List[Token], i: int) -> Tuple[StatementsNode, int]:
  """Compile the statements in a subroutine body."""
  node = StatementsNode()
  while tokens[i] != SymbolToken('}'):
    if tokens[i] == KeywordToken('let'):
      child, i = CompileLetStatement(tokens, i)
      node.AddChild(child)
      continue
    if tokens[i] == KeywordToken('do'):
      child, i = CompileDoStatement(tokens, i)
      node.AddChild(child)
      continue
    if tokens[i] == KeywordToken('return'):
      child, i = CompileReturnStatement(tokens, i)
      node.AddChild(child)
      continue
    if tokens[i] == KeywordToken('while'):
      child, i = CompileWhileStatement(tokens, i)
      node.AddChild(child)
      continue
    if tokens[i] == KeywordToken('if'):
      child, i = CompileIfStatement(tokens, i)
      node.AddChild(child)
      continue
    raise SyntaxError('Invalid statement')
  return node, i


def CompileLetStatement(
    tokens: List[Token], i: int) -> Tuple[LetStatementNode, int]:
  """Compile a let statement."""
  node = LetStatementNode()
  node.AddChild(KeywordNode('let'))
  i += 1

  syntax_err = SyntaxError('Invalid let statement')
  if not isinstance(tokens[i], IdentifierToken):
    raise syntax_err
  node.AddChild(IdentifierNode(tokens[i].Value()))
  i += 1

  if tokens[i] == SymbolToken('['):
    node.AddChild(SymbolNode('['))
    i += 1
    child, i = CompileExpression(tokens, i)
    node.AddChild(child)
    if tokens[i] != SymbolToken(']'):
      raise syntax_err
    node.AddChild(SymbolNode(']'))
    i += 1

  if tokens[i] != SymbolToken('='):
    raise syntax_err
  node.AddChild(SymbolNode('='))
  i += 1

  child, i = CompileExpression(tokens, i)
  node.AddChild(child)

  if tokens[i] != SymbolToken(';'):
    raise syntax_err
  node.AddChild(SymbolNode(';'))
  i += 1

  return node, i


def CompileDoStatement(
    tokens: List[Token], i: int) -> Tuple[DoStatementNode, int]:
  """Compile do statement tokens into a syntax subtree."""
  node = DoStatementNode()
  node.AddChild(KeywordNode('do'))
  i += 1
  children, i = CompileSubroutineCall(tokens, i)
  node.AddChildren(*children)

  if tokens[i] != SymbolToken(';'):
    raise SyntaxError('Expected ;')
  node.AddChild(SymbolNode(';'))
  i += 1

  return node, i


def CompileReturnStatement(
    tokens: List[Token], i: int) -> Tuple[ReturnStatementNode, int]:
  """Compile return statement tokens into a syntax subtree."""
  node = ReturnStatementNode()
  node.AddChild(KeywordNode('return'))
  i += 1

  if tokens[i] != SymbolToken(';'):
    child, i = CompileExpression(tokens, i)
    node.AddChild(child)

  if tokens[i] != SymbolToken(';'):
    raise SyntaxError('Expected ;')
  node.AddChild(SymbolNode(';'))
  i += 1

  return node, i


def CompileWhileStatement(tokens: List[Token], i: int) -> Tuple[WhileStatementNode, int]:
  """Compile while statement syntax subtree from tokens."""
  node = WhileStatementNode()
  node.AddChild(KeywordNode('while'))
  i += 1

  children, i = CompileParenExpression(tokens, i)
  node.AddChildren(*children)

  children, i = CompileBlock(tokens, i)
  node.AddChildren(*children)

  return node, i


def CompileIfStatement(tokens: List[Token], i: int) -> Tuple[IfStatementNode, int]:
  """Compile if statement subtree from list of tokens."""
  node = IfStatementNode()
  node.AddChild(KeywordNode('if'))
  i += 1

  children, i = CompileParenExpression(tokens, i)
  node.AddChildren(*children)

  children, i = CompileBlock(tokens, i)
  node.AddChildren(*children)

  if tokens[i] == KeywordToken('else'):
    node.AddChild(KeywordNode('else'))
    i += 1
    children, i = CompileBlock(tokens, i)
    node.AddChildren(*children)

  return node, i


def CompileParenExpression(
    tokens: List[Token], i: int) -> Tuple[List[SyntaxTreeNode], int]:
  """Compile an expression wrapped in parentheses."""
  nodes = []
  if tokens[i] != SymbolToken('('):
    raise SyntaxError('Expected (')
  nodes.append(SymbolNode('('))
  i += 1

  child, i = CompileExpression(tokens, i)
  nodes.append(child)

  if tokens[i] != SymbolToken(')'):
    raise SyntaxError('Expected )')
  nodes.append(SymbolNode(')'))
  i += 1

  return nodes, i


def CompileBlock(
    tokens: List[Token], i: int) -> Tuple[List[SyntaxTreeNode], int]:
  """Compile statements wrapped in curly braces, i.e. a block."""
  nodes = []
  if tokens[i] != SymbolToken('{'):
    raise SyntaxError('Expected {')
  nodes.append(SymbolNode('{'))
  i += 1

  child, i = CompileStatements(tokens, i)
  nodes.append(child)

  if tokens[i] != SymbolToken('}'):
    raise SyntaxError('Expected }')
  nodes.append(SymbolNode('}'))
  i += 1

  return nodes, i


def CompileExpression(
    tokens: List[Token], i: int) -> Tuple[ExpressionNode, int]:
  """Compile an expression into a syntax tree."""
  node = ExpressionNode()
  child, i = CompileTerm(tokens, i)
  node.AddChild(child)
  if any(tokens[i] == SymbolToken(symbol) for symbol in BINARY_OPS):
    node.AddChild(SymbolNode(tokens[i].Value()))
    i += 1
    child, i = CompileTerm(tokens, i)
    node.AddChild(child)
  return node, i


def CompileTerm(tokens: List[Token], i: int) -> Tuple[TermNode, int]:
  """Compile an expression term"""
  node = TermNode()
  syntax_err = SyntaxError('Invalid term')
  if isinstance(tokens[i], IntegerConstantToken):
    node.AddChild(IntegerConstantNode(tokens[i].Value()))
    i += 1
  elif isinstance(tokens[i], StringConstantToken):
    node.AddChild(StringConstantNode(tokens[i].Value()))
    i += 1
  elif any(tokens[i] == KeywordToken(kw) for kw in KEYWORD_CONSTANTS):
    node.AddChild(KeywordNode(tokens[i].Value()))
    i += 1
  elif isinstance(tokens[i], IdentifierToken):
    if tokens[i+1] == SymbolToken('(') or tokens[i+1] == SymbolToken('.'):
      nodes, i = CompileSubroutineCall(tokens, i)
      node.AddChildren(*nodes)
    else:
      node.AddChild(IdentifierNode(tokens[i].Value()))
      i += 1
      if tokens[i] == SymbolToken('['):
        node.AddChild(SymbolNode('['))
        i += 1
        child, i = CompileExpression(tokens, i)
        node.AddChild(child)
        if tokens[i] != SymbolToken(']'):
          raise syntax_err
        node.AddChild(SymbolNode(']'))
        i += 1
  elif tokens[i] == SymbolToken('('):
    children, i = CompileParenExpression(tokens, i)
    node.AddChildren(*children)
  elif any(tokens[i] == SymbolToken(symbol) for symbol in UNARY_OPS):
    node.AddChild(SymbolNode(tokens[i].Value()))
    i += 1
    child, i = CompileTerm(tokens, i)
    node.AddChild(child)
  else:
    raise syntax_err
  return node, i


def CompileSubroutineCall(
    tokens: List[Token], i: int) -> Tuple[List[SyntaxTreeNode], int]:
  """Compile a subroutine call."""
  nodes = []
  syntax_err = SyntaxError('Invalid subroutine call')
  nodes.append(IdentifierNode(tokens[i].Value()))
  i += 1
  if tokens[i] == SymbolToken('.'):
    nodes.append(SymbolNode('.'))
    i += 1
    if not isinstance(tokens[i], IdentifierToken):
      raise syntax_err
    nodes.append(IdentifierNode(tokens[i].Value()))
    i += 1
  if tokens[i] != SymbolToken('('):
    raise syntax_err
  nodes.append(SymbolNode('('))
  i += 1
  expression_list = ExpressionListNode()
  while tokens[i] != SymbolToken(')'):
    child, i = CompileExpression(tokens, i)
    expression_list.AddChild(child)
    if tokens[i] == SymbolToken(','):
      expression_list.AddChild(SymbolNode(','))
      i += 1
      continue
    if tokens[i] == SymbolToken(')'):
      break
    raise syntax_err
  nodes.append(expression_list)
  nodes.append(SymbolNode(')'))
  i += 1
  return nodes, i


def SyntaxTreeToXML(node: SyntaxTreeNode) -> XMLTag:
  """Convert a syntax tree into an XML tag tree."""
  xml = XMLTag(node.TagName())
  if isinstance(node, NonTerminalNode):
    for child in node.children:
      xml.AddChild(SyntaxTreeToXML(child), 2)
  if isinstance(node, TerminalNode):
    xml.Text(node.Value())
  return xml


def WriteSyntaxXML(jack_file_path: str, syntax_xml: XMLTag) -> str:
  """Write the tokenized .jack file into a .xml file."""
  out_dir, jack_filename = os.path.split(jack_file_path)
  out_path = os.path.join(out_dir, jack_filename.replace('.jack', '.xml'))
  syntax_out = str(syntax_xml) + '\n'
  with open(out_path, 'w') as f:
    f.write(syntax_out)


def main():
  """Main function"""
  for file_path in ParseJackFilePathsFromArguments():
    print(f'Compiling {file_path}')
    tokens = Tokenize(file_path)
    WriteTokensXML(file_path, tokens)
    syntax_tree = CompileClass(tokens)
    WriteSyntaxXML(file_path, SyntaxTreeToXML(syntax_tree))


if __name__ == '__main__':
  main()
