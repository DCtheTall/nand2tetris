"""
VM Translator: Stack Arithmetic and Memory Segments
---------------------------------------------------

"""


import os
import sys

from typing import List, Tuple


SEGMENT_POINTERS = {
    'local': 'LCL',
    'argument': 'ARG',
    'this': 'THIS',
    'that': 'THAT',
}


class InvalidInputError(Exception):
  """Custom exception type for when users input invalid command line arguments."""

  def __init__(self):
    super(InvalidInputError, self).__init__(
        'Must be called `python hack_assembler.py path/to/in.vm ')


def ParseArguments() -> Tuple[str]:
  """Parse command line arguments and return the input and output file paths."""
  if len(sys.argv) != 2:
    raise InvalidInputError()
  inp_path = sys.argv[1]
  if not inp_path.endswith('.vm'):
    raise InvalidInputError()
  outp_path = inp_path.replace('.vm', '.asm')
  return inp_path, outp_path


def RemoveComment(line: str) -> str:
  """Strip a comment from a line of ASM code."""
  try:
    return line[:line.index('//')]
  except ValueError:
    return line


def PreprocessInput(file_content: str) -> List[List[str]]:
  """Split the .vm content by line, each line into tokens, and remove all comments."""
  result = []
  for line in file_content.split('\n'):
    line = RemoveComment(line.strip())
    if line:
      result.append(line.split())
  return result


def FileLabel(input_path):
  """Derives the file label for static memory from the input path."""
  _, fname = os.path.split(input_path)
  return fname[:-3]


def TranslateVMtoASM(vm_tokens: List[List[str]], file_label) -> str:
  """Translate tokens in the VM file into Hack Assembly."""
  result = []
  for tokens in vm_tokens:
    op = tokens[0]
    if op == 'push':
      segment = tokens[1]
      offset = int(tokens[2])
      result.extend(LoadValueToD(segment, offset, file_label))
      result.extend(PushDRegisterToStack())
    elif op == 'pop':
      segment = tokens[1]
      offset = int(tokens[2])
      result.extend(LoadAddressIntoR15(segment, offset, file_label))
      result.extend(PopStackToDRegister())
      result.extend([ 
          # Set the value at the address in R15.
          '@R15',
          'A=M',
          'M=D',
      ])
    elif op in ['add', 'sub', 'and', 'or']:
      result.extend(PopStackToDRegister())
      # Overwrite the top of the stack with the result.
      result.append('A=A-1')
      if op == 'add':
        result.append('M=M+D')
      elif op == 'sub':
        result.append('M=M-D')
      elif op == 'and':
        result.append('M=M&D')
      elif op == 'or':
        result.append('M=M|D')
    elif op == 'neg':
      result.extend(['@SP', 'M=-M'])
    # TODO comparison ops
    else:
      raise SyntaxError('Unexpected operation: {}'.format(op))
  result.append('')
  return '\n'.join(result)


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


def PushDRegisterToStack():
  """Push value in the D register onto the stack."""
  return ['@SP', 'A=M', 'M=D', '@SP', 'M=M+1']


def LoadAddressIntoR15(segment: str, offset: int, file_label: str) -> List[str]:
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

  result.extend(['@R15', 'M=D'])
  return result


def PopStackToDRegister():
  """Pop the stack into the D register."""
  return ['@SP', 'AM=M-1', 'D=M']


def main():
  """Main function parses the arguments, translate VM code to assembly, and write the output."""
  inp_path, outp_path = ParseArguments()
  with open(inp_path, 'r') as f:
    asm_content = TranslateVMtoASM(PreprocessInput(f.read()), FileLabel(inp_path))
  with open(outp_path, 'w') as f:
    f.write(asm_content)


if __name__ == '__main__':
  main()
