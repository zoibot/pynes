import sys

class Machine(object):
'''Class for actually simulating the machine'''
    pc = 0
    a = s = p = 0
    x = y = 0
    mem = [0]

    flags = { 'N' = 1 << 7,
              'V' = 1 << 6,
              'B' = 1 << 4,
              'D' = 1 << 3,
              'I' = 1 << 2,
              'Z' = 1 << 1,
              'C' = 1 << 0 }
    def set_flag(flag, val):
       if val:
            p = p | flags[flag]
        else:
            p = p & (~flags[flag])
    def get_flag(flag):
        return p & flags[flag]

    def execute(self, inst):
        try:
            self.__getattr__(inst.type)(inst)
        except:
            pass
            #should log this
    def nop(inst):
        pass

class Instruction(object):
'''Class for parsing instructions'''
    { 0x4D : ('nop','') }
    type = 'nop'
    opcode = 0x00 
    addr_mode = '#'
    operand = 0
    def read(rom):
        return Instruction(
    def __init__(op, addr_mode, addr):
        pass
    def parse_address(self, rom):
        if addr_mode == 'imm':
            operand = addr
        else if addr_mode == 'abs':
            operand = mem[addr]
        else if addr_mode == 'zp':
            operand = mem[addr]
        else if addr_mode == 'imp':
            operand = None
        else if addr_mode == 'abs_inx':
            operand = mem[addr+x]
        else if addr_mode == 'abs_iny':
            operand = mem[addr+y]
        else if addr_mode == 'zpix':
            operand = mem[addr+y]
        else if addr_mode == 'zpiy':
            operand = mem[addr+y]
        else if addr_mode == 'ixind':
        else if addr_mode == 'indix':
        else if addr_mode == 'rel':
            operand = pc + addr
        else if addr_mode == 'acc':
            operand = a
        else:
            print 'Error, unrecognized addressing mode'
            sys.exit(1)
            

filename = sys.argv[1]

rom = open(filename).read()

while rom:
    inst = Instruction.read(rom)
    machine.execute(inst)
