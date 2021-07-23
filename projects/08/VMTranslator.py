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

from typing import List


class InvalidInputError(Exception):
  """Custom exception type for when users input invalid command line arguments."""

  def __init__(self, msg: str):
    super(InvalidInputError, self).__init__(
        msg if msg else 'Must be called `python hack_assembler.py '
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
  result.extend(vm_filenames)
  dirname = os.path.split(dir_path)[0].split('/')[-1]
  outp_path = os.path.join(dir_path, dirname + '.asm')
  result.append(outp_path)
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


def TranslateVMFiletoASM(vm_file_path: str) -> str:
  """"""
  return ''


def TranslateVMFilesToASM(vm_file_paths: List[str]) -> str:
  """"""
  return ''


def main():
  """Main function parses the IO paths from arguments, translates VM code to assembly, and writes the output file."""
  paths = ParseIOPathsFromArguments()
  inp_paths, outp_path = paths[:-1], paths[-1]
  if len(inp_paths) == 1:
    asm_content = TranslateVMFiletoASM(inp_paths[0])
  else:
    asm_content = TranslateVMFilesToASM(inp_paths)
  with open(outp_path, 'w') as f:
    f.write(asm_content)

if __name__ == '__main__':
  main()
