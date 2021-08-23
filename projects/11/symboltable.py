"""
Jack Compiler
=============
Symbol table module
-------------------
This file contains an implementation of the class and subroutine symbol tables
used to compile Jack code.

"""


from enum import Enum
from typing import NamedTuple, Union

from codeparser import IdentifierNode, KeywordNode, TerminalNode


class VariableType(Enum):
  """Different variable types in Jack."""
  INT = 'int'
  CHAR = 'char'
  BOOL = 'boolean'
  IDENTIFIER = 'identifier'


def VariableTypeFromNode(node: TerminalNode):
  """Get the VariableType from a TerminalNode in the syntax tree."""
  if node == KeywordNode('int'):
    return VariableType.INT
  if node == KeywordNode('char'):
    return VariableType.CHAR
  if node == KeywordNode('boolean') or node == KeywordNode('bool'):
    return VariableType.BOOL
  if isinstance(node, IdentifierNode):
    return VariableType.IDENTIFIER
  raise SyntaxError('Unexpected variable type')


class VariableKind(Enum):
  """Different kinds of variables in Jack."""
  FIELD = 'field'
  STATIC = 'static'
  LOCAL = 'local'
  ARGUMENT = 'argument'


class Variable(NamedTuple):
  """Data type representing an entry of the symbol table."""
  name: str
  type: VariableType
  kind: VariableKind
  index: int
  cls_name: str


class SymbolTable:
  """Base symbol table class."""
  def __init__(self):
    self.symbols = {}
    self.cur_indices = {k: 0 for k in VariableKind}

  def Add(self, name: str, type: VariableType, kind: VariableKind,
          cls_name: Union[str, None]):
    """Add a variable to the symbol table."""
    if name in self.symbols:
      raise SyntaxError('Adding duplicate symbol')
    idx = self.cur_indices[kind]
    self.cur_indices[kind] += 1
    var_cls_name = ''
    if type == VariableType.IDENTIFIER:
      assert isinstance(cls_name, str)
      var_cls_name = cls_name
    self.symbols[name] = Variable(name, type, kind, idx, var_cls_name)
      

  def Get(self, name: str) -> Union[Variable, None]:
    """Get a variable from the symbol table."""
    if name not in self.symbols:
      return None
    return self.symbols[name]

  def GetNumberOfFields(self):
    """Get the number of class fields in the symbol table."""
    result = 0
    for symbol in self.symbols.values():
      if symbol.kind == VariableKind.FIELD:
        result += 1
    return result
