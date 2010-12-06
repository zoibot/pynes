import sys
import struct

class Machine(object):
    '''Class for actually simulating the machine'''
#for nestest
    pc = 0xC000
    a = s = p = 0
    x = y = 0
    mem = [0]

    flags = { 'N': 1 << 7,
              'V': 1 << 6,
              'B': 1 << 4,
              'D': 1 << 3,
              'I': 1 << 2,
              'Z': 1 << 1,
              'C': 1 << 0 }
    def set_flag(self, flag, val):
        if val:
            p = p | flags[flag]
        else:
            p = p & (~flags[flag])
    def get_flag(self, flag):
        return p & flags[flag]

    def get_mem(self, addr):
        if addr >= 0xC000:
            return self.rom.prg_rom[addr-0xC000]
        if addr >= 0x8000:
            return self.rom.prg_rom[addr-0x8000]
    def set_mem(self, addr, val):
        mem[addr] = val

    def __init__(self, rom):
        self.rom = rom

    def run(self):
        #self.running = True
        #while self.running
        for i in range(10):
            inst = self.next_inst()
            print inst
        #self.execute(inst)

    def next_inst(self):
        op = self.get_mem(self.pc)
        inst = Instruction(op)
        self.pc += 1
        inst.parse_operand('00')
        self.pc += inst.addr_len
        return inst
        
    def execute(self, inst):
        try:
            self.__getattr__(inst.type)(inst)
        except:
            pass
            #should log this

    def nop(inst):
        pass
    def jmp(inst):
        self.pc = inst.operand
    def cld(inst):
        self.set_flag('D', False)
    def ldx(inst):
        self.x = inst.operand

class Instruction(object):
    '''Class for parsing instructions'''
    opcodes = { 0x4C : ('jmp', 'imm'),
                0xd8 : ('cld', 'imp'),
                0xa2 : ('ldx', 'imm')}
    type = 'nop'
    opcode = 0x00 
    addr_mode = ''
    operand = 0
    def __init__(self, op):
        self.opcode = op
        try:
            self.op, self.addr_mode = self.opcodes[op]
        except:
            print 'unsupported opcode: ' + hex(op)
            sys.exit(1)
        self.addr_len = 0
    def parse_operand(self, addr):
        """if addr_mode == 'imm':
            operand = addr
        elif addr_mode == 'abs':
            operand = mem[addr]
        elif addr_mode == 'zp':
            operand = mem[addr]
        elif addr_mode == 'imp':
            operand = None
        elif addr_mode == 'abs_inx':
            operand = mem[addr+x]
        elif addr_mode == 'abs_iny':
            operand = mem[addr+y]
        elif addr_mode == 'zpix':
            operand = mem[addr+y]
        elif addr_mode == 'zpiy':
            operand = mem[addr+y]
        elif addr_mode == 'ixind':
            pass
        elif addr_mode == 'indix':
            pass
        elif addr_mode == 'rel':
            operand = pc + addr
        elif addr_mode == 'acc':
            operand = a"""
        if self.addr_mode == 'imm':
            self.operand = addr
            self.addr_len = 4
        elif self.addr_mode == 'imp':
            self.operand = ''
            self.addr_len = 0
        else:
            print 'Error, unrecognized addressing mode'
            sys.exit(1)
    def __repr__(self):
        return self.op + ' ' + self.operand

class Rom(object):
    '''class for reading in iNES files'''
    def __init__(self, f):
        self.f = f
        header = f.read(16)
        if header[:4] == 'NES\x1a':
            print 'header constant OK!'
        else:
            print 'bad rom...'
        (self.prg_size, self.chr_size, self.flags6, self.flags7, 
            self.prg_ram_size, self.flags9, 
            self.flags10) = struct.unpack('7b5x', header[4:])
        if self.flags6 & 1 << 2:
            print 'loading trainer'
            self.trainer = f.read(512)
        else:
            self.trainer = None
        print 'loading prg'
        self.prg_rom = map(lambda x: struct.unpack('B', x)[0], f.read(16384 * self.prg_size))
        print 'loading chr'
        self.chr_rom = f.read(8192 * self.chr_size)

filename = sys.argv[1]

rom = Rom(open(filename))
mach = Machine(rom)
#print hex(ord(mach.get_mem(mach.pc)))
mach.run()
