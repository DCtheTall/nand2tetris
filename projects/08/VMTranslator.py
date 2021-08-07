"""
VM Translator
-------------
This file implements a translator from Jack VM code
to Hack assembly language.

This translator supports the entire VM language
specified in the Nand2Tetris course, which includes:
- Stack push/pop commands
- Stack arithmetic
- Memory segments
- Label commands
- Function commands

"""


import os
import sys

from typing import Dict, List


SEGMENT_POINTERS = {
    'local': 'LCL',
    'argument': 'ARG',
    'this': 'THIS',
    'that': 'THAT',
}

# This address is used as a "data register" for the stack during pop operations.
STACK_DATA_REGISTER = 'R15'
# This register stores the address of the current LCL pointer when a function returns.
# That address is used to restore segment pointers of the function's caller.
LCL_TMP_REGISTER = 'R13'
# This register stores the address of the label in the assembly code to resume execution
# after a function returns in case the called function had no arguments.
RETURN_ADDR_TMP_REGISTER = 'R14'


class InvalidInputError(Exception):
  """Custom exception type for when users input invalid command line arguments."""

  def __init__(self, msg: str):
    super(InvalidInputError, self).__init__(
        msg if msg else 'Must be called `python VMTranslator.py '
                        'path/to/in.vm or path/to/in/')


def ParseIOPathsFromArguments() -> List[str]:
  """Parse command line arguments and return the input and output file paths.
  
  Input paths to VM files are all elements of the returned list except the last element.
  The last element is the path to write the output assembly file to.
  """
  if len(sys.argv) != 2:
    raise InvalidInputError()
  inp_path = sys.argv[1]
  if os.path.isdir(inp_path):
    if not inp_path.endswith('/'):
      inp_path += '/'
    return ParseIOPathsFromDir(inp_path)
  if inp_path.endswith('.vm'):
    outp_path = inp_path.replace('.vm', '.asm')
    return [inp_path, outp_path]
  raise InvalidInputError()


def ParseIOPathsFromDir(dir_path: str) -> List[str]:
  """Parse the input paths to the VM files in a directory."""
  vm_filenames = [fname for fname in os.listdir(dir_path)
                        if fname.endswith('.vm')]
  if 'Sys.vm' not in vm_filenames:
    raise InvalidInputError('Directory must contain a Sys.vm file')
  result = [os.path.join(dir_path, fname) for fname in vm_filenames]
  dirname = os.path.split(dir_path)[0].split('/')[-1]
  outp_path = os.path.join(dir_path, dirname + '.asm')
  result.append(outp_path)
  return result


def TranslateVMFiletoASM(vm_file_path: str, call_counts: Dict[str, int]) -> List[str]:
  """Translate the content of a single VM code file into assembly."""
  with open(vm_file_path, 'r') as f:
    vm_file_content = f.read()
  vm_tokens = PreprocessInput(vm_file_content)
  file_label = FileLabel(vm_file_path)
  result = []
  comparison_counter = 0
  for tokens in vm_tokens:
    op = tokens[0]
    if op in ['push', 'pop']:
      segment = tokens[1]
      offset = int(tokens[2])
      if op == 'push':
        result.extend(PushOp(segment, offset, file_label))
      else:  # op == pop
        result.extend(PopOp(segment, offset, file_label))
    elif op in ['add', 'sub', 'and', 'or']:
      result.extend(BinaryOp(op))
    elif op in ['neg', 'not']:
      result.extend(UnaryOp(op))
    elif op in ['eq', 'lt', 'gt']:
      result.extend(ComparisonOp(op, comparison_counter, file_label))
      comparison_counter += 1
    elif op in ['label', 'goto', 'if-goto']:
      label = tokens[1]
      if op == 'label':
        result.extend(LabelOp(file_label, label))
      elif op == 'goto':
        result.extend(GotoOp(file_label, label))
      else:  # op == if-goto
        result.extend(IfGotoOp(file_label, label))
    elif op in ['function', 'call']:
      fn_name = tokens[1]
      n = int(tokens[2])
      if op == 'function':
        result.extend(FunctionOp(fn_name, n, file_label))
      else:  # op == call
        try:
          call_counts[fn_name] += 1
        except KeyError:
          call_counts[fn_name] = 0
        result.extend(CallOp(fn_name, call_counts[fn_name], n))
    elif op == 'return':
      result.extend(ReturnOp())
    else:
      raise SyntaxError('Unexpected operation: {}'.format(op))
  return result


def PreprocessInput(file_content: str) -> List[List[str]]:
  """Split the .vm content by line, each line into tokens, and remove all comments."""
  result = []
  for line in file_content.split('\n'):
    line = RemoveComment(line.strip())
    if line:
      result.append(line.split())
  return result


def RemoveComment(line: str) -> str:
  """Strip a comment from a line of ASM code."""
  try:
    return line[:line.index('//')]
  except ValueError:
    return line


def FileLabel(input_path):
  """Derives the file label for static memory from the input path."""
  _, fname = os.path.split(input_path)
  return fname[:-3]


def PushOp(segment: str, offset: int, file_label: str) -> List[str]:
  """Translates a stack push operation into assembly code."""
  result = LoadValueToD(segment, offset, file_label)
  result.extend(PushDRegisterToStack())
  return result


def LoadValueToD(segment: str, offset: int, file_label: str) -> List[str]:
  """Load a value from the pointer specified by (segment, offset) into the D register."""
  if segment == 'constant':
    return ['@{}'.format(offset), 'D=A']
  if segment == 'temp':
    return ['@{}'.format(5 + offset), 'D=M']
  if segment in SEGMENT_POINTERS:
    return [
        '@{}'.format(SEGMENT_POINTERS[segment]),
        'D=M',
        '@{}'.format(offset),
        'A=A+D',
        'D=M',
    ]
  if segment == 'static':
    return [
        '@{}.{}'.format(file_label, offset),
        'D=M',
    ]
  if segment != 'pointer':
    raise SyntaxError('Unexpected segment: {}'.format(segment))
  return [
      '@{}'.format('THAT' if offset else 'THIS'),
      'D=M',
  ]

def PushDRegisterToStack() -> List[str]:
  """Push value in the D register onto the stack."""
  return ['@SP', 'A=M', 'M=D', '@SP', 'M=M+1']


def PopOp(segment: str, offset: int, file_label: str) -> List[str]:
  """Translates a stack pop operation into assembly code."""
  result = LoadAddressIntoStackDataRegister(segment, offset, file_label)
  result.extend(PopStackToDRegister())
  result.extend(['@{}'.format(STACK_DATA_REGISTER), 'A=M', 'M=D'])
  return result


def LoadAddressIntoStackDataRegister(segment: str, offset: int, file_label: str) -> List[str]:
  """Load the address of the pointer determined by (segment, offset) into RAM[15]."""
  result = []
  if segment == 'temp':
    result = ['@{}'.format(5 + offset), 'D=A']
  elif segment in SEGMENT_POINTERS:
    result = [
        '@{}'.format(SEGMENT_POINTERS[segment]),
        'D=M',
        '@{}'.format(offset),
        'D=D+A',
    ]
  elif segment == 'static':
    result = [
        '@{}.{}'.format(file_label, offset),
        'D=A',
    ]
  elif segment == 'pointer':
    result = [
        '@{}'.format('THAT' if offset else 'THIS'),
        'D=A',
    ]
  else:
    raise SyntaxError('Unexpected segment: {}'.format(segment))
  result.extend(['@{}'.format(STACK_DATA_REGISTER), 'M=D'])
  return result


def PopStackToDRegister() -> List[str]:
  """Pop the stack into the D register."""
  return ['@SP', 'AM=M-1', 'D=M']


def BinaryOp(op: str) -> List[str]:
  """Translates a binary stack arithmetic operation into assembly."""
  result = []
  result.extend(PopStackToDRegister())
  # Overwrite the top of the stack with the result.
  result.extend(SetARegisterToTopOfStack())
  if op == 'add':
    result.append('M=M+D')
  elif op == 'sub':
    result.append('M=M-D')
  elif op == 'and':
    result.append('M=M&D')
  else:  # op == or
    result.append('M=M|D')
  return result


def UnaryOp(op: str) -> List[str]:
  """Translates a unary stack arithmetic operation into assembly."""
  result = SetARegisterToTopOfStack()
  result.append('M=-M' if op == 'neg' else 'M=!M')
  return result


def SetARegisterToTopOfStack() -> List[str]:
  """Set the A register to the address at the top of the stack."""
  return ['@SP', 'A=M-1']


def ComparisonOp(op: str, index: int, file_label: str) -> List[str]:
  """Translate stack arithmetic comparison operations to assembly."""
  if op == 'eq':
    jump_cmd = 'JEQ'
  elif op == 'lt':
    jump_cmd = 'JLT'
  else:  # op == gt
    jump_cmd = 'JGT'
  result = PopStackToDRegister()
  result.extend(SetARegisterToTopOfStack())
  result.extend([
      'D=M-D',
      '@{}.InsertTrue.{}'.format(file_label, index),
      'D;{}'.format(jump_cmd),
  ])
  result.extend(SetARegisterToTopOfStack())
  result.extend([
      'M=0',
      '@{}.End.{}'.format(file_label, index),
      '0;JMP',
      '({}.InsertTrue.{})'.format(file_label, index),
  ])
  result.extend(SetARegisterToTopOfStack())
  result.extend([
      'M=-1',
      '({}.End.{})'.format(file_label, index),
  ])
  return result


def LabelOp(file_label: str, label: str) -> List[str]:
  """Translates a VM code label operation to assembly code."""
  return ['({}.{})'.format(file_label, label)]


def GotoOp(file_label: str, label: str) -> List[str]:
  """Translates a VM code if operation to assembly code."""
  return ['@{}.{}'.format(file_label, label), '0;JMP']


def IfGotoOp(file_label: str, label: str) -> List[str]:
  """Translates a VM code if-goto operation to assembly code."""
  result = PopStackToDRegister()
  result.extend([
      '@{}.{}'.format(file_label, label),
      'D;JNE',
  ])
  return result


def FunctionOp(fn_name: str, n_vars: int, file_label: str) -> List[str]:
  """Translates a VM code function operation to assembly code."""
  result = ['({})'.format(fn_name)]
  for _ in range(n_vars):
    result.extend(PushOp('constant', 0, file_label))
  return result


def CallOp(fn_name: str, index: int, n_args: int) -> List[str]:
  """Translate a VM code call operation to assembly code."""
  # Add the stack frame
  return_addr = '{}.ret.{}'.format(fn_name, index)
  result = ['@{}'.format(return_addr), 'D=A']
  result.extend(PushDRegisterToStack())
  for addr in ['LCL', 'ARG', 'THIS', 'THAT']:
    result.extend(['@{}'.format(addr), 'D=M'])
    result.extend(PushDRegisterToStack())

  result.extend([
      # Set ARG -> SP - 5 - nArgs
      '@SP',
      'D=M',
      '@5',
      'D=D-A',
      '@{}'.format(n_args),
      'D=D-A',
      '@ARG',
      'M=D',
      # Set LCL -> SP
      '@SP',
      'D=M',
      '@LCL',
      'M=D',
      # Go to function label
      '@{}'.format(fn_name),
      '0;JMP',
      # Label for return address
      '({})'.format(return_addr)
  ])
  return result


def ReturnOp() -> List[str]:
  """Translate the VM code return operation to assembly code."""
  # Save return address, stored in LCL-5, to RETURN_ADDR_TMP_REGISTER
  # in case there were no arguments.
  result = [
      '@LCL',
      'D=M',
      '@5',
      'A=D-A',
      'D=M',
      '@{}'.format(RETURN_ADDR_TMP_REGISTER),
      'M=D',
  ]
  # Save top of working stack to ARG+0
  result.extend(PopStackToDRegister())
  result.extend(['@ARG', 'A=M', 'M=D'])
  result.extend([
      # Set SP to ARG+1
      '@ARG',
      'D=M+1',
      '@SP',
      'M=D',
      # Store current value in LCL in the LCL_TMP_REGISTER register.
      '@LCL',
      'D=M',
      '@{}'.format(LCL_TMP_REGISTER),
      'M=D',
  ])
  # Restore segment pointers
  for i, addr in enumerate(['THAT', 'THIS', 'ARG', 'LCL']):
    result.extend([
        '@{}'.format(LCL_TMP_REGISTER),
        'D=M',
        '@{}'.format(i + 1),
        'A=D-A',
        'D=M',
        '@{}'.format(addr),
        'M=D',
    ])
  # Jump to return address, stored in RETURN_ADDR_TMP_REGISTER
  result.extend(['@{}'.format(RETURN_ADDR_TMP_REGISTER), 'A=M', '0;JMP'])
  return result


def TranslateVMFilesToASM(vm_file_paths: List[str]) -> List[str]:
  """Translates a directory of VM files into a single assembly program."""
  idx = -1
  call_counts = {}
  for i, path in enumerate(vm_file_paths):
    if path.endswith('Sys.vm'):
      idx = i
      break
  if idx == -1:
    raise FileNotFoundError('Cannot find Sys.vm')
  vm_file_paths = vm_file_paths.copy()
  vm_file_paths[0], vm_file_paths[idx] = vm_file_paths[idx], vm_file_paths[0]
  result = BootCode()
  for vm_file in vm_file_paths:
    result.extend(TranslateVMFiletoASM(vm_file, call_counts))
  return result


def BootCode() -> List[str]:
  """Boot code sets SP -> 256, LCL -> -1, ARG -> -2, THIS -> -3, THAT -> -4 and calls Sys.init"""
  result = BootPointer('SP', 256)
  for ptr_name, value in [('LCL', -1), ('ARG', -2), ('THIS', -3),
                          ('THAT', -4)]:
    result.extend(BootPointer(ptr_name, value))
  result.extend(CallOp('Sys.init', 0, 0))
  return result


def BootPointer(ptr_name: str, value: int) -> List[str]:
  """Boot the pointer to  the provided value."""
  if value >= 0:
    result = ['@{}'.format(value), 'D=A']
  else:
    result = ['@{}'.format(-value), 'D=-A']
  result.extend(['@{}'.format(ptr_name), 'M=D'])
  return result


def WriteOutput(asm_tokens: List[str], outp_path: str):
  """Writes the resulting assembly tokens to the output .asm path."""
  asm_tokens.append('')
  asm_content = '\n'.join(asm_tokens)
  with open(outp_path, 'w') as f:
    f.write(asm_content)


def main():
  """Main function parses the IO paths from arguments, translates VM code to assembly, and writes the output file."""
  paths = ParseIOPathsFromArguments()
  inp_paths, outp_path = paths[:-1], paths[-1]
  if len(inp_paths) == 1:
    asm_tokens = TranslateVMFiletoASM(inp_paths[0], {})
  else:
    asm_tokens = TranslateVMFilesToASM(inp_paths)
  WriteOutput(asm_tokens, outp_path)

if __name__ == '__main__':
  main()
