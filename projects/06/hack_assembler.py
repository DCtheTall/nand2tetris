"""
Hack Assembler
--------------
This file is a script to translate Hack Assembly files into Hack Machine Language files.
This script assumes that there are no syntax errors in the Hack Assembly file.

Example usage:

python hack_assembler.py path/to/in.asm path/to/out.hack

"""

import sys


class InvalidInputError(Exception):
  """Custom exception type for when users input invalid command line arguments."""

  def __init__(self):
    super(InvalidInputError, self).__init__(
        'Must be called `python hack_assembler.py path/to/in.asm '
        'path/to/out.hack`')


def ParseArguments():
  """Parse command line arguments and return the input and output file paths."""
  if len(sys.argv) != 3:
    raise InvalidInputError()
  inp_path, outp_path = sys.argv[1:]
  if not (inp_path.endswith('.asm')
          and outp_path.endswith('.hack')):
    raise InvalidInputError()
  return inp_path, outp_path


def StripComment(line):
  """Strip a comment from a line of ASM code."""
  try:
    return line[:line.index('//')]
  except ValueError:
    return line


def PreprocessInput(file_content):
  """Split the .asm content by line and remove all whitespace."""
  return [StripComment(''.join(l.strip().split()))
          for l in file_content.split('\n')]


class Assembler:
  """Class that handles parsing the input .asm file and generate the content of the .hack file."""
  
  def __init__(self, inp_path, outp_path):
    self.inp_path_ = inp_path
    self.outp_path_ = outp_path
    with open(self.inp_path_) as f:
      self.asm_content_ = PreprocessInput(f.read())
    self.cur_line_ = None
    self.symbols_ = {'R' + str(i): i for i in range(16)}
    self.symbols_.update({
        'SCREEN': 16384,
        'KBD': 24576,
        'SP': 0,
        'LCL': 1,
        'ARG': 2,
        'THIS': 3,
        'THAT': 4,
    })
    self.labels_ = set()
    self.var_addr_ = 16
    self.output_ = []
    self.c_bit_table_ = {
        '0': 0b101010, '1': 0b111111, '-1': 0b111010, 'D': 0b001100,
        'A': 0b110000, 'M': 0b110000, '!D': 0b001101, '!A': 0b110001,
        '!M': 0b110001, '-D': 0b001111, '-A': 0b110011, '-M': 0b110011,
        'D+1': 0b011111, 'A+1': 0b110111, 'M+1': 0b110111, 'D-1': 0b001110,
        'A-1': 0b110010, 'M-1': 0b110010, 'D+A': 0b000010, 'D+M': 0b000010,
        'D-A': 0b010011, 'D-M': 0b010011, 'A-D': 0b000111, 'M-D': 0b000111,
        'D&A': 0b000000, 'D&M': 0b000000, 'D|A': 0b010101, 'D|M': 0b010101,
    }
    self.a_bit_set_ = {
        'M', '!M', '-M', 'M+1', 'M-1',
        'D+M', 'D-M', 'M-D', 'D&M', 'D|M',
    }

  def FirstPass(self):
    """First pass searches for labels and stores their address."""
    n = 0
    for i, line in enumerate(self.asm_content_):
      if not line:
        continue
      if line[0] != '(':
        n += 1
        continue
      self.labels_.add(i)
      symbol = line[1:-1]
      if symbol in self.symbols_:
        raise SyntaxError(
            'Cannot overwrite a predefined symbol \'{}\' with a '
            'label'.format(symbol))
      self.symbols_[symbol] = n

  def SecondPass(self):
    """Process the symbols in all lines that aren't labels."""
    for i, line in enumerate(self.asm_content_):
      self.cur_line_ = line
      if not self.cur_line_ or i in self.labels_:
        continue
      if self.cur_line_[0] == '@':
        self.ProcessA_()
      else:
        self.ProcessC_()

  def ProcessA_(self):
    """Process an A instruction."""
    addr = self.cur_line_[1:]
    try:
      addr = int(addr)
      self.output_.append(addr % (1 << 16))
    except ValueError:
      if addr in self.symbols_:
        self.output_.append(self.symbols_[addr])
        return
      self.symbols_[addr] = self.var_addr_
      self.output_.append(self.var_addr_ % (1 << 16))
      self.var_addr_ += 1

  def ProcessC_(self):
    """Process a C instruction."""
    result = 57344  # Set first 3 most significant bits.
    try:
      i = self.cur_line_.index(';')
      computation, jump = self.cur_line_[:i], self.cur_line_[i+1:] 
    except ValueError:
      computation, jump = self.cur_line_, ''

    try:
      i = computation.index('=')
      dest, comp = computation[:i], computation[i+1:]
    except ValueError:
      dest, comp = '', computation
    if dest:
      d_bits = [
          'null', 'M',  'D',  'MD',
          'A',    'AM', 'AD', 'AMD',
      ].index(dest) << 3
      result += d_bits

    c_bits = self.c_bit_table_[comp] << 6
    result += c_bits
    if comp in self.a_bit_set_:
      result += 4096  # Set a-bit

    if jump:
      j_bits = [
          'null', 'JGT', 'JEQ', 'JGE',
          'JLT',  'JNE', 'JLE', 'JMP',
      ].index(jump)
      result += j_bits

    self.output_.append(result)

  def WriteOutput(self):
    """Write the output of the translation to the .hack file."""
    output_tmp = []
    for x in self.output_:
      x = '{0:b}'.format(x)
      x = '0' * (16 - len(x)) + x
      output_tmp.append(x)
    with open(self.outp_path_, 'w') as f:
      f.write('\n'.join(output_tmp))


def main():
  """Main entry point, instantiates Assembler class and calls methods."""
  assembler = Assembler(*ParseArguments())
  assembler.FirstPass()
  assembler.SecondPass()
  assembler.WriteOutput()


if __name__ == '__main__':
  main()
