// This file is part of www.nand2tetris.org
// and the book "The Elements of Computing Systems"
// by Nisan and Schocken, MIT Press.
// File name: projects/04/Fill.asm

// Runs an infinite loop that listens to the keyboard input.
// When a key is pressed (any key), the program blackens the screen,
// i.e. writes "black" in every pixel;
// the screen should remain fully black as long as the key is pressed. 
// When no key is pressed, the program clears the screen, i.e. writes
// "white" in every pixel;
// the screen should remain fully clear as long as no key is pressed.

// Put your code here.

// Pseudocode algorithm
// OUTER_LOOP
//   if @KBD == 0:
//     for i in {@SCREEN, @SCREEN + 1, ..., @SCREEN + 8191}:
//       RAM[i] = 0
//   else
//     for i in {@SCREEN, @SCREEN + 1, ..., @SCREEN + 8191}:
//       RAM[i] = -1

(OUTER_LOOP)
  // Set @i to 0, used in either loop
  @i
  M=0

  // Set the D register to the keyboard value
  @KBD
  D=M
  // if D == 0 jump to WHITE
  @WHITE
  D;JEQ

  // otherwise set color to -1
  @color
  M=-1
  @INNER_LOOP
  0;JMP

  (WHITE)
    @color
    M=0

  // Color screen black
  (INNER_LOOP)
    // If i == 8192 then continue OUTER_LOOP
    @i
    D=M
    @8192
    D=D-A
    @OUTER_LOOP
    D;JEQ

    // Store the current pixel address in a variable
    @SCREEN
    D=A
    @i
    D=D+M
    @addr
    M=D

    // Set the pixel to @color
    @color
    D=M
    @addr
    A=M
    M=D

    // Increment i
    @i
    M=M+1

    // Continue coloring screen black
    @INNER_LOOP
    0;JMP
