"""
Jack Compiler
=============
Parser module
-------------
This file contains all the code for converting a list of Jack tokens (see tokenizer),
and converts it into an abstract syntax tree which will be parsed for code writing.

"""


from typing import List, Tuple

from constants import BINARY_OPS, KEYWORD_CONSTANTS, UNARY_OPS
from tokenizer import (IdentifierToken, IntegerConstantToken, InvalidInputError,
                       KeywordToken, StringConstantToken, SymbolToken, Token)


class SyntaxTreeNode:
  """Base class for a node in the abstract syntax tree."""
  pass


class TerminalNode(SyntaxTreeNode):
  pass

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
  pass

class ClassVarDecNode(NonTerminalNode):
  pass

class SubroutineDecNode(NonTerminalNode):
  pass

class ParameterListNode(NonTerminalNode):
  pass

class SubroutineBodyNode(NonTerminalNode):
  pass

class VarDecNode(NonTerminalNode):
  pass

class StatementsNode(NonTerminalNode):
  pass

class LetStatementNode(NonTerminalNode):
  pass

class DoStatementNode(NonTerminalNode):
  pass

class ReturnStatementNode(NonTerminalNode):
  pass

class WhileStatementNode(NonTerminalNode):
  pass

class IfStatementNode(NonTerminalNode):
  pass

class ExpressionNode(NonTerminalNode):
  pass

class TermNode(NonTerminalNode):
  pass

class ExpressionListNode(NonTerminalNode):
  pass


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
  """Compile the variable declarations and statements in the body of a subroutine."""
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


def TestParser():
  import os
  from tokenizer import Tokenize
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
  syntax_tree = CompileClass(tokens)
  assert isinstance(syntax_tree, ClassNode)
  assert len(syntax_tree.children) > 0
  print('Test passed!')

  os.remove(tmp_jack_file_path)


if __name__ == '__main__':
  TestParser()
