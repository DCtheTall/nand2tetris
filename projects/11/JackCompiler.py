"""
Jack Compiler
=============
Main script
-----------
This file contains all of the code which is for project 11 except for symboltable.py.

This file implements the CodeWriter class, a class which traverses the syntax tree built
in codeparser.py and translates the syntax tree into VM code which implements the Jack
program.

"""


import os
import sys

from enum import Enum
from typing import List

from codeparser import (ClassNode, ClassVarDecNode, CompileClass,
                        DoStatementNode, ExpressionListNode, ExpressionNode,
                        IdentifierNode, IfStatementNode, IntegerConstantNode,
                        KeywordNode, LetStatementNode, ParameterListNode,
                        ReturnStatementNode, StatementsNode, StringConstantNode,
                        SubroutineBodyNode, SubroutineDecNode, SymbolNode,
                        TermNode, VarDecNode, WhileStatementNode)
from constants import KEYWORD_CONSTANTS, UNARY_OPS
from symboltable import SymbolTable, Variable, VariableKind, VariableType, VariableTypeFromNode
from tokenizer import InvalidInputError, Tokenize


def ParseJackFilePathsFromArguments() -> List[str]:
  """Parse command line arguments and return the paths to all the Jack files to analyze."""
  if len(sys.argv) != 2:
    raise InvalidInputError()
  inp_path = sys.argv[1]
  if not os.path.isdir(inp_path):
    if not inp_path.endswith('.jack') or not os.path.exists(inp_path):
      raise InvalidInputError()
    return [inp_path]
  jack_filenames = [fname for fname in os.listdir(inp_path)
                          if fname.endswith('.jack')]
  if 'Main.jack' not in jack_filenames:
    raise InvalidInputError('Directory must contain a Main.jack file')
  return [os.path.join(inp_path, fname) for fname in jack_filenames]


class VMSegment(Enum):
  ARGUMENT = 'argument'
  LOCAL = 'local'
  THIS = 'this'
  THAT = 'that'
  CONSTANT = 'constant'
  STATIC = 'static'
  TEMP = 'temp'
  POINTER = 'pointer'


def VMSegmentFromKind(kind: VariableKind) -> VMSegment:
  if kind == VariableKind.FIELD:
    return VMSegment.THIS
  if kind == VariableKind.STATIC:
    return VMSegment.STATIC
  if kind == VariableKind.LOCAL:
    return VMSegment.LOCAL
  else:  # kind == VMSegment.ARGUMENT:
    return VMSegment.ARGUMENT


class CodeWriter:
  """Class that handles parsing syntax tree and writing code."""

  def __init__(self, syntax_tree: ClassNode):
    self.output = []
    self.cls_symbol_table = SymbolTable()
    self.subroutine_symbol_table = None
    self.class_name = None
    self.subroutine_name = None
    self.subroutine_label_count = 0

    self.TranslateSyntaxTree(syntax_tree)

  def __str__(self):
    """Write the output to the string content of a .vm file."""
    result = '\n'.join(self.output)
    if result:
      result += '\n'
    return result

  def GetSymbol(self, name: str) -> Variable:
    """Get a symbol from the symbol tables."""
    result = self.subroutine_symbol_table.Get(name)
    if result is not None:
      return result
    result = self.cls_symbol_table.Get(name)
    if result is None:
      raise SyntaxError(f'Undefined symbol {name}')
    return result

  def Write(self, *args):
    """Write new VM code instructions."""
    self.output.extend(args)

  def WritePush(self, segment: VMSegment, index: int):
    """Write a stack push op."""
    self.Write(f'push {segment.value} {index}')

  def WritePop(self, segment: VMSegment, index: int):
    """Write a stack pop op."""
    self.Write(f'pop {segment.value} {index}')

  def WriteCall(self, cls_name: str, subroutine_name: str, n_args: int):
    """Write a function call op."""
    self.Write(f'call {cls_name}.{subroutine_name} {n_args}')

  def WriteLabel(self, label: str):
    """Writes a label VM command."""
    self.Write(f'label {self.class_name}.{self.subroutine_name}.{label}')

  def WriteGoto(self, label: str):
    """Writes a goto VM command."""
    self.Write(f'goto {self.class_name}.{self.subroutine_name}.{label}')

  def WriteIfGoto(self, label: str):
    """Writes an if-goto VM command."""
    self.Write(f'if-goto {self.class_name}.{self.subroutine_name}.{label}')

  def TranslateSyntaxTree(self, syntax_tree: ClassNode):
    """Translate a class syntax tree into VM code."""
    self.class_name = syntax_tree.children[1].Value()
    for node in syntax_tree.children:
      if isinstance(node, ClassVarDecNode):
        self.AddClassSymbol(node)
        continue
      if isinstance(node, SubroutineDecNode):
        self.TranslateSubroutine(node)
  
  def AddClassSymbol(self, node: ClassVarDecNode):
    """Add a class variable to the symbol table."""
    kind = VariableKind.FIELD
    if node.children[0] == KeywordNode('static'):
      kind = VariableKind.STATIC
    var_type = VariableTypeFromNode(node.children[1])
    cls_name = None
    if var_type == VariableType.IDENTIFIER:
      cls_name = node.children[1].Value()
    for child in node.children[2:]:
      if isinstance(child, IdentifierNode):
        self.cls_symbol_table.Add(child.Value(), var_type, kind, cls_name)

  def TranslateSubroutine(self, node: SubroutineDecNode):
    """Translate a subroutine declaration into VM code."""
    self.subroutine_label_count = 0
    self.subroutine_name = node.children[2].Value()
    self.subroutine_symbol_table = SymbolTable()

    subroutine_body = node.children[6]
    assert isinstance(subroutine_body, SubroutineBodyNode)
    for child in subroutine_body.children:
      if isinstance(child, VarDecNode):
        self.AddLocalVariableSymbol(child)
    n_vars = self.subroutine_symbol_table.GetNumberOfLocals()

    self.Write(f'function {self.class_name}.{self.subroutine_name} {n_vars}')

    if node.children[0] == KeywordNode('constructor'):
      self.SetupConstructor()

    is_method = node.children[0] == KeywordNode('method')
    if is_method:
      self.WritePush(VMSegment.ARGUMENT, 0)
      self.WritePop(VMSegment.POINTER, 0)

    parameter_list = node.children[4]
    assert isinstance(parameter_list, ParameterListNode)
    self.AddArgumentSymbols(parameter_list, is_method)
    
    for child in subroutine_body.children:
      if isinstance(child, StatementsNode):
        self.TranslateStatements(child)

  def SetupConstructor(self):
    """Add setup code for a class constructor that allocates memory in the heap for the instance."""
    n_fields = self.cls_symbol_table.GetNumberOfFields()
    self.WritePush(VMSegment.CONSTANT, n_fields)
    self.WriteCall('Memory', 'alloc', 1)
    self.WritePop(VMSegment.POINTER, 0)

  def AddArgumentSymbols(self, parameter_list: ParameterListNode, is_method: False):
    """Add argument symbols to the subroutine symbol table."""
    if is_method:
      self.subroutine_symbol_table.cur_indices[VariableKind.ARGUMENT] = 1
    for i, child in enumerate(parameter_list.children):
      if i % 3 == 0:
        var_type = VariableTypeFromNode(child)
        cls_name = None
        if var_type == VariableType.IDENTIFIER:
          cls_name = child.Value()
      if i % 3 == 1:
        self.subroutine_symbol_table.Add(
            child.Value(), var_type, VariableKind.ARGUMENT, cls_name)

  def AddLocalVariableSymbol(self, var_dec: VarDecNode):
    """Add local variable symbols to the symbol table."""
    var_type = VariableTypeFromNode(var_dec.children[1])
    cls_name = None
    if var_type == VariableType.IDENTIFIER:
      cls_name = var_dec.children[1].Value()
    for child in var_dec.children[2:]:
      if isinstance(child, IdentifierNode):
        self.subroutine_symbol_table.Add(
            child.Value(), var_type, VariableKind.LOCAL, cls_name)

  def TranslateStatements(self, node: StatementsNode):
    """Translate a statements node by looking at each child statement."""
    for child in node.children:
      if isinstance(child, LetStatementNode):
        self.TranslateLetStatement(child)
      elif isinstance(child, DoStatementNode):
        self.TranslateDoStatement(child)
      elif isinstance(child, ReturnStatementNode):
        self.TranslateReturnStatement(child)
      elif isinstance(child, WhileStatementNode):
        self.TranslateWhileStatement(child)
      else:
        assert isinstance(child, IfStatementNode)
        self.TranslateIfStatement(child)

  def TranslateLetStatement(self, node: LetStatementNode):
    """Translate a let statement into VM instructions."""
    var_name = node.children[1].Value()
    var = self.GetSymbol(var_name)
    if node.children[2] == SymbolNode('['):
      self.WritePush(VMSegmentFromKind(var.kind), var.index)

      expr1 = node.children[3]
      assert isinstance(expr1, ExpressionNode)
      self.TranslateExpression(expr1)
      expr2 = node.children[6]
      assert isinstance(expr2, ExpressionNode)
      self.TranslateExpression(expr2)

      # Write sum of array address and result of expression 2 to temp 0
      self.WritePop(VMSegment.TEMP, 0)
      self.WritePush(VMSegmentFromKind(var.kind), var.index)
      self.Write('add')
      # Set `that` pointer to result of expression 1.
      self.WritePop(VMSegment.POINTER, 1)

      # Write the result expression 2 into the array.
      self.WritePush(VMSegment.TEMP, 0)
      self.WritePop(VMSegment.THAT, 0)
      return
      
    assert node.children[2] == SymbolNode('=')
    expr = node.children[3]
    assert isinstance(expr, ExpressionNode)
    self.TranslateExpression(expr)
    self.WritePop(VMSegmentFromKind(var.kind), var.index)

  def TranslateDoStatement(self, node: DoStatementNode):
    """Translate a do statement into VM instructions."""
    term = node.children[1]
    assert isinstance(term, TermNode)
    self.TranslateSubroutineCall(term)
    self.WritePop(VMSegment.TEMP, 0)

  def TranslateReturnStatement(self, node: ReturnStatementNode):
    """Translate a return statement into VM instructions."""
    if isinstance(node.children[1], ExpressionNode):
      self.TranslateExpression(node.children[1])
    else:  # void function
      assert node.children[1] == SymbolNode(';')
      self.WritePush(VMSegment.CONSTANT, 0)
    self.Write('return')

  def TranslateWhileStatement(self, node: WhileStatementNode):
    """Translate a while statement into VM instructions."""
    expr = node.children[2]
    assert isinstance(expr, ExpressionNode)

    while_label1 = f'While.1.{self.subroutine_label_count}'
    while_label2 = f'While.2.{self.subroutine_label_count}'
    self.subroutine_label_count += 1

    statements = node.children[5]
    assert isinstance(statements, StatementsNode)

    self.WriteLabel(while_label1)
    self.TranslateExpression(expr)
    self.Write('not')
    self.WriteIfGoto(while_label2)
    self.TranslateStatements(statements)
    self.WriteGoto(while_label1)
    self.WriteLabel(while_label2)

  def TranslateIfStatement(self, node: IfStatementNode):
    """Translate an if statement into VM instructions."""
    expr = node.children[2]
    assert isinstance(expr, ExpressionNode)

    statements1 = node.children[5]
    assert isinstance(statements1, StatementsNode)

    if len(node.children) == 7:  # No `else { ... }`
      statements2 = StatementsNode()
    else:
      statements2 = node.children[9]
      assert isinstance(statements2, StatementsNode)

    if_label1 = f'If.1.{self.subroutine_label_count}'
    if_label2 = f'If.2.{self.subroutine_label_count}'
    self.subroutine_label_count += 1

    self.TranslateExpression(expr)
    self.Write('not')
    self.WriteIfGoto(if_label1)
    self.TranslateStatements(statements1)
    self.WriteGoto(if_label2)
    self.WriteLabel(if_label1)
    self.TranslateStatements(statements2)
    self.WriteLabel(if_label2)

  def TranslateExpression(self, node: ExpressionNode):
    """Translate an expression into VM code."""
    if len(node.children) == 1:
      term = node.children[0]
      assert isinstance(term, TermNode)
      self.TranslateTerm(term)
      return
    
    assert len(node.children) % 2 == 1
    op_stack = []
    for i, child in enumerate(node.children):
      if i % 2 == 0:
        assert isinstance(child, TermNode)
        self.TranslateTerm(child)
      else:
        assert isinstance(child, SymbolNode)
        op_stack.append(child)
    while op_stack:
      op = op_stack.pop()
      self.TranslateOp(op)
  
  def TranslateTerm(self, node: TermNode):
    """Translate a term into the VM implementation."""
    # Simplest, has a single terminal node as a child.
    if len(node.children) == 1:
      self.TranslateSimpleTerm(node)
      return

    if isinstance(node.children[0], SymbolNode):
      child = node.children[0]
      if child.Value() in UNARY_OPS:
        assert isinstance(node.children[1], TermNode)
        self.TranslateTerm(node.children[1])
        
        if child.Value() == '-':
          self.Write('neg')
        else:
          assert child.Value() == '~'
          self.Write('not')
        return
      
      assert child == SymbolNode('(')
      assert len(node.children) == 3 and node.children[2] == SymbolNode(')')
      self.TranslateExpression(node.children[1])
      return

    assert isinstance(node.children[0], IdentifierNode)

    if (node.children[1] == SymbolNode('.')
        or node.children[1] == SymbolNode('(')):
      self.TranslateSubroutineCall(node)
      return

    arr = node.children[0]
    assert isinstance(arr, IdentifierNode)
    var = self.GetSymbol(arr.Value())
    self.WritePush(VMSegmentFromKind(var.kind), var.index)

    assert node.children[1] == SymbolNode('[')
    expr = node.children[2]
    assert isinstance(expr, ExpressionNode)
    self.TranslateExpression(expr)
    self.Write('add')

    self.WritePop(VMSegment.POINTER, 1)
    self.WritePush(VMSegment.THAT, 0)

  def TranslateSimpleTerm(self, node: TermNode):
    """Translate a `simple` term i.e. a term with only one child."""
    child = node.children[0]
    if isinstance(child, IntegerConstantNode):
      val = int(child.Value())
      self.WritePush(VMSegment.CONSTANT, abs(val))
      if val < 0:
        self.Write('neg')
    elif isinstance(child, StringConstantNode):
      str_len = len(child.Value())
      self.WritePush(VMSegment.CONSTANT, str_len)
      self.WriteCall('String', 'new', 1)
      for c in child.Value():
        char = ord(c)
        self.WritePush(VMSegment.CONSTANT, char)
        # First parameter is the "this" pointer for the String instance.
        self.WriteCall('String', 'appendChar', 2)
    elif isinstance(child, KeywordNode):
      kw = child.Value()
      assert kw in KEYWORD_CONSTANTS
      if kw == 'true':
        self.WritePush(VMSegment.CONSTANT, 1)
        self.Write('neg')
      elif kw == 'false':
        self.WritePush(VMSegment.CONSTANT, 0)
      elif kw == 'null':
        self.WritePush(VMSegment.CONSTANT, 0)
      elif kw == 'this':
        self.WritePush(VMSegment.POINTER, 0)
    else:
      assert isinstance(child, IdentifierNode)
      var = self.GetSymbol(child.Value())
      self.WritePush(VMSegmentFromKind(var.kind), var.index)

  def TranslateSubroutineCall(self, node: TermNode):
    """Translate a subroutine call into VM instructions."""
    if node.children[1] == SymbolNode('.'):
      try:
        var_name = node.children[0].Value()
        var = self.GetSymbol(var_name)
        self.WritePush(VMSegmentFromKind(var.kind), var.index)
        cls_name = var.cls_name
        n_method_args = 1
      except SyntaxError:  # If lookup fails then must be a function call, not a method call.
        cls_name = node.children[0].Value()
        n_method_args = 0
      subroutine_name = node.children[2].Value()
      expr_list = node.children[4]
      assert isinstance(expr_list, ExpressionListNode)
      n_args = self.TranslateExpressionList(expr_list)
      self.WriteCall(cls_name, subroutine_name, n_args + n_method_args)

    if node.children[1] == SymbolNode('('):
      subroutine_name = node.children[0].Value()
      expr_list = node.children[2]
      assert isinstance(expr_list, ExpressionListNode)
      self.WritePush(VMSegment.POINTER, 0)
      n_args = self.TranslateExpressionList(expr_list)
      self.WriteCall(self.class_name, subroutine_name, n_args + 1)

  def TranslateExpressionList(self, node: ExpressionListNode) -> int:
    """Translate an expression list for a subroutine call."""
    n_args = 0
    for child in node.children:
      if isinstance(child, ExpressionNode):
        n_args += 1
        self.TranslateExpression(child)
    return n_args
  
  def TranslateOp(self, node: SymbolNode):
    """Translate a binary op symbol to VM instructions."""
    symbol = node.Value()
    if symbol == '+':
      self.Write('add')
    elif symbol == '-':
      self.Write('sub')
    elif symbol == '*':
      self.WriteCall('Math', 'multiply', 2)
    elif symbol == '/':
      self.WriteCall('Math', 'divide', 2)
    elif symbol == '&':
      self.Write('and')
    elif symbol == '|':
      self.Write('or')
    elif symbol == '<':
      self.Write('lt')
    elif symbol == '>':
      self.Write('gt')
    else:
      assert symbol == '='
      self.Write('eq')


def WriteVMFile(jack_file_path: str, vm_file_content: str):
  """Write the VM file content to the correct path."""
  vm_file_path = jack_file_path.replace('.jack', '.vm')
  with open(vm_file_path, 'w') as f:
    f.write(vm_file_content)


def main():
  """Main function called when you run the compiler."""
  jack_files = ParseJackFilePathsFromArguments()
  for jack_file in jack_files:
    print(f'Compiling {jack_file}...')
    tokens = Tokenize(jack_file)
    syntax_tree = CompileClass(tokens)
    code_writer = CodeWriter(syntax_tree)
    WriteVMFile(jack_file, str(code_writer))


if __name__ == '__main__':
  main()
