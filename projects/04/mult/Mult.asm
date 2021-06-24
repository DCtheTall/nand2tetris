// This file is part of www.nand2tetris.org
// and the book "The Elements of Computing Systems"
// by Nisan and Schocken, MIT Press.
// File name: projects/04/Mult.asm

// Multiplies R0 and R1 and stores the result in R2.
// (R0, R1, R2 refer to RAM[0], RAM[1], and RAM[2], respectively.)
//
// This program only needs to handle arguments that satisfy
// R0 >= 0, R1 >= 0, and R0*R1 < 32768.

// Put your code here.

// Pseudocode algorithm
// prod := 0
// for i in {0, 1, ..., R0 - 1}:
//   prod += R1

// Set @R2 to 0
@R2
M=0

// Set variable @i to 0
@i
M=0

// Start for loop
(LOOP)
  // Compute @i - @R0
  @R0
  D=M
  @i
  D=D-M

  // Break loop if @i - @R0 == 0
  @END
  D;JEQ

  // Set @R2 = @R2 + @R1 
  @R2
  D=M
  @R1
  D=M+D
  @R2
  M=D

  // Increment @i
  @i
  M=M+1

  // Continue the loop
  @LOOP
  0;JMP

// End for loop
(END)
  @END
  0;JMP
