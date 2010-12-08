import sys
import struct

def hex2(i):
    return '%02X' % (i & 0xFF)
def hex4(i):
    return '%04X' % (i & 0xFFFF)

class Machine(object):
    '''Class for actually simulating the machine'''
#for nestest
    pc = 0xC000
    prev_pc = pc
    a = 0
    s = 0
    p = 0x24
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
            self.p = self.p | self.flags[flag]
        else:
            self.p = self.p & (~self.flags[flag])
    def get_flag(self, flag):
        return self.p & self.flags[flag]
    def set_nz(self, val):
        self.set_flag('Z', val == 0)
        self.set_flag('N', val & (1 << 7))

    #TODO mem should be its own class and slicable
    def get_mem(self, addr):
        if addr >= 0xC000:
            return self.rom.prg_rom[addr-0xC000]
        if addr >= 0x8000:
            return self.rom.prg_rom[addr-0x8000]
        else:
            return self.mem[addr]
    def set_mem(self, addr, val):
        self.mem[addr] = val

    def push2(self, val):
        # val is 16 bit
        self.s -= 2
        s = self.s | 0x0100
        self.set_mem(s+1, val & 0xFF)
        self.set_mem(s+2, val >> 8)
    def pop2(self):
        # val is 16 bit
        self.s += 2
        s = self.s | 0x0100
        return self.get_mem(s-1) + (self.get_mem(s) << 8)
    def push(self, val):
        self.s -= 1
        s = self.s | 0x0100
        self.set_mem(s+1, val)
    def pop(self):
        self.s += 1
        s = self.s | 0x0100
        return self.get_mem(s)


    def dump_regs(self):
        res = ''
        res += ' A:'+hex2(self.a)
        res += ' X:'+hex2(self.x)
        res += ' Y:'+hex2(self.y)
        res += ' P:'+hex2(self.p)
        res += ' SP:'+hex2(self.s)
        return res

    def __init__(self, rom):
        self.rom = rom
        self.mem = [0xff] * (0x8000)

    def run(self):
        #self.running = True
        #while self.running
        self.reset()
        self.running = True
        while self.running:
            print hex4(self.pc),
            print '',
            inst = self.next_inst()
            print inst,
            print '  ',
            print self.dump_regs()
            self.execute(inst)
        #self.execute(inst)

    def next_inst(self):
        self.prev_pc = self.pc
        op = self.get_mem(self.pc)
        inst = Instruction(op)
        self.pc += 1
        inst.parse_operand([self.get_mem(a) for a in range(self.pc, self.pc+2)], self)
        self.pc += inst.addr_len
        return inst
        
    def execute(self, inst):
        try:
            getattr(self, inst.op)(inst)
        except AttributeError, e:
            print 'unimplemented instruction: '+inst.op
            print e
            sys.exit(1)
            #should log this

    def reset(self):
        self.s -= 3
        self.s &= 0xff
        self.mem = [0xff] * (0x8000)
        self.mem[0x0008] = 0xf7
        self.mem[0x0009] = 0xef
        self.mem[0x000a] = 0xdf
        self.mem[0x000f] = 0xbf

    def nop(self, inst):
        pass

    def jmp(self, inst):
        self.pc = inst.addr
    def jsr(self, inst):
        self.push2(self.pc-1)
        self.pc = inst.addr
    def rts(self, inst):
        self.pc = self.pop2()+1
    def rti(self, inst):
        self.p = (self.pop() | (1 << 5)) & ~(self.flags['B'])
        self.pc = self.pop2()

    def bcs(self, inst):
        if self.get_flag('C'):
            self.pc = inst.operand
    def bcc(self, inst):
        if not self.get_flag('C'):
            self.pc = inst.operand
    def beq(self, inst):
        if self.get_flag('Z'):
            self.pc = inst.operand
    def bne(self, inst):
        if not self.get_flag('Z'):
            self.pc = inst.operand
    def bvs(self, inst):
        if self.get_flag('V'):
            self.pc = inst.operand
    def bvc(self, inst):
        if not self.get_flag('V'):
            self.pc = inst.operand
    def bpl(self, inst):
        if not self.get_flag('N'):
            self.pc = inst.operand
    def bmi(self, inst):
        if self.get_flag('N'):
            self.pc = inst.operand
    def bit(self, inst):
        m = self.get_mem(inst.operand)
        self.set_flag('N', m & (1 << 7))
        self.set_flag('V', m & (1 << 6))
        self.set_flag('Z', m & self.a == 0)

    def compare(self, a, b):
        ua = a if a < 0x80 else (a - 0x100)
        ub = b if b < 0x80 else (b - 0x100)
        self.set_flag('N', (ua - ub) & (1 << 7) )
        self.set_flag('Z', ua == ub)
        self.set_flag('C', a >= b)
    def cmp(self, inst):
        self.compare(self.a, inst.operand)
    def cpy(self, inst):
        self.compare(self.y, inst.operand)
    def cpx(self, inst):
        self.compare(self.x, inst.operand)

    def clc(self, inst):
        self.set_flag('C', False)
    def cld(self, inst):
        self.set_flag('D', False)
    def clv(self, inst):
        self.set_flag('V', False)
    def sed(self, inst):
        self.set_flag('D', True)
    def sec(self, inst):
        self.set_flag('C', True)
    def sei(self, inst):
        self.set_flag('I', True)

    def lda(self, inst):
        self.a = inst.operand
        self.set_nz(self.a)
    def sta(self, inst):
        self.set_mem(inst.operand, self.a)
    def ldx(self, inst):
        self.x = inst.operand
        self.set_nz(self.x)
    def stx(self, inst):
        self.set_mem(inst.addr, self.x)
    def ldy(self, inst):
        self.y = inst.operand
        self.set_nz(self.y)
    def sty(self, inst):
        self.set_mem(inst.operand, self.y)

    def php(self, inst):
        self.push(self.p | self.flags['B'])
    def plp(self, inst):
        self.p = (self.pop() | (1 << 5)) & ~(self.flags['B'])
    def pla(self, inst):
        self.a = self.pop()
        self.set_nz(self.a)
    def pha(self, inst):
        self.push(self.a)

    def and_(self, inst):
        self.a = self.a & inst.operand
        self.set_nz(self.a)
    def ora(self, inst):
        self.a = self.a | inst.operand
        self.set_nz(self.a)
    def eor(self, inst):
        self.a = self.a ^ inst.operand
        self.set_nz(self.a)
    def adc(self, inst):
        a7 = self.a & (1 << 7)
        m7 = inst.operand & (1 << 7)
        self.a = self.a + inst.operand + (1 if self.get_flag('C') else 0)
        self.set_flag('C', self.a > 0xff)
        self.a = self.a & 0xff
        self.set_nz(self.a)
        r7 = self.a & (1 << 7)
        self.set_flag('V', not ((a7 != m7) or (a7 == m7 == r7)))
    def sbc(self, inst):
        a7 = self.a & (1 << 7)
        m7 = inst.operand & (1 << 7)
        old_a = self.a
        self.a = self.a - inst.operand - (0 if self.get_flag('C') else 1)
        self.set_flag('C',old_a >= inst.operand)
        self.a = self.a & 0xff
        self.set_nz(self.a)
        r7 = self.a & (1 << 7)
        self.set_flag('V', not ((a7 == m7) or (a7 != m7 and r7 == a7)))
    def inx(self, inst):
        self.x += 1
        self.x &= 0xff
        self.set_nz(self.x)
    def iny(self, inst):
        self.y += 1
        self.y &= 0xff
        self.set_nz(self.y)
    def dex(self, inst):
        self.x -= 1
        self.x &= 0xff
        self.set_nz(self.x)
    def dey(self, inst):
        self.y -= 1
        self.y &= 0xff
        self.set_nz(self.y)  
    def lsr_a(self, inst):
        self.set_flag('C', self.a & (1))
        self.a >>= 1
        self.set_nz(self.a)
    def asl_a(self, inst):
        self.set_flag('C', self.a & (1 << 7))
        self.a <<= 1
        self.a &= 0xff
        self.set_nz(self.a)
    def ror_a(self, inst):
        new_c = self.a & 1
        self.a >>= 1
        self.a |= (1 << 7) if self.get_flag('C') else 0
        self.set_flag('C', new_c)
        self.set_nz(self.a)
    def rol_a(self, inst):
        new_c = self.a & (1 << 7)
        self.a <<= 1
        self.a |= 1 if self.get_flag('C') else 0
        self.a &= 0xff
        self.set_flag('C', new_c)
        self.set_nz(self.a)
    
    def tay(self, inst):
        self.y = self.a
        self.set_nz(self.y)
    def tax(self, inst):
        self.x = self.a
        self.set_nz(self.x)
    def tsx(self, inst):
        self.x = self.s
        self.set_nz(self.x)
    def txs(self, inst):
        self.s = self.x
    def tya(self, inst):
        self.a = self.y
        self.set_nz(self.a)
    def txa(self, inst):
        self.a = self.x
        self.set_nz(self.a)
 
class Instruction(object):
    '''Class for parsing instructions'''
    opcodes = { 0x08 : ('php', 'imp'),
                0x09 : ('ora', 'imm'),
                0x0a : ('asl_a', 'a'),
                0x10 : ('bpl', 'rel'),
                0x18 : ('clc', 'imp'),
                0x20 : ('jsr', 'abs'),
                0x24 : ('bit', 'zp'),
                0x28 : ('plp', 'imp'),
                0x29 : ('and_', 'imm'),
                0x2a : ('rol_a', 'a'),
                0x30 : ('bmi', 'rel'),
                0x38 : ('sec', 'imp'),
                0x40 : ('rti', 'imp'),
                0x48 : ('pha', 'imp'),
                0x49 : ('eor', 'imm'),
                0x4a : ('lsr_a', 'a'),
                0x4C : ('jmp', 'abs'),
                0x50 : ('bvc', 'rel'),
                0x60 : ('rts', 'imp'),
                0x68 : ('pla', 'imp'),
                0x69 : ('adc', 'imm'),
                0x6a : ('ror_a', 'a'),
                0x70 : ('bvs', 'rel'),
                0x78 : ('sei', 'imp'),
                0x84 : ('sty', 'imm'),
                0x85 : ('sta', 'zp'),
                0x86 : ('stx', 'zp'),
                0x88 : ('dey', 'imp'),
                0x8a : ('txa', 'imp'),
                0x8d : ('sta', 'abs'),
                0x8e : ('stx', 'abs'),
                0x90 : ('bcc', 'rel'),
                0x98 : ('tya', 'imp'),
                0x9a : ('txs', 'imp'),
                0xa0 : ('ldy', 'imm'),
                0xa1 : ('lda', 'ixid'),
                0xa2 : ('ldx', 'imm'),
                0xa5 : ('lda', 'zp'),
                0xa8 : ('tay', 'imp'),
                0xa9 : ('lda', 'imm'),
                0xaa : ('tax', 'imp'),
                0xad : ('lda', 'abs'),
                0xae : ('ldx', 'abs'),
                0xb0 : ('bcs', 'rel'),
                0xb8 : ('clv', 'imp'),
                0xba : ('tsx', 'imp'),
                0xc0 : ('cpy', 'imm'),
                0xc8 : ('iny', 'imp'),
                0xc9 : ('cmp', 'imm'),
                0xca : ('dex', 'imp'),
                0xd8 : ('cld', 'imp'),
                0xe0 : ('cpx', 'imm'),
                0xe8 : ('inx', 'imp'),
                0xe9 : ('sbc', 'imm'),
                0xea : ('nop', 'imp'),
                0xd0 : ('bne', 'rel'),
                0xf0 : ('beq', 'rel'),
                0xf8 : ('sed', 'imp')}
    type = 'nop'
    opcode = 0x00 
    addr_mode = ''
    operand = 0
    def __init__(self, op):
        self.opcode = op
        try:
            self.op, self.addr_mode = self.opcodes[op]
        except:
            print 'unsupported opcode: ' + hex2(op)
            sys.exit(1)
        self.addr_len = 0
    def parse_operand(self, addr, mach):
        self.args = addr
        if self.addr_mode == 'imm2':
            self.operand = addr[0] + (addr[1] << 8)
            self.addr_len = 2
        elif self.addr_mode == 'imm':
            self.operand = addr[0]
            self.addr_len = 1
        elif self.addr_mode in ['imp', 'a']:
            self.operand = None
            self.addr_len = 0
        elif self.addr_mode == 'zp':
            self.addr = addr[0]
            self.operand = mach.get_mem(self.addr)
            self.addr_len = 1
        elif self.addr_mode == 'abs':
            self.addr = addr[0] + (addr[1] << 8)
            self.operand = mach.get_mem(self.addr)
            self.addr_len = 2
        elif self.addr_mode == 'rel':
            self.operand = addr[0] + mach.pc + 1
            self.addr_len = 1
        elif self.addr_mode == 'ixid':
            self.addr = addr[0] + mach.x
            print hex2(self.addr)
            t = mach.get_mem(self.addr) + (mach.get_mem(self.addr+1) << 8) 
            print hex4(t)
            self.operand = mach.get_mem(t)
            print hex2(self.operand)
            self.addr_len = 1
        else:
            print 'Error, unrecognized addressing mode'
            sys.exit(1)
    def __repr__(self):
        #TODO rewrite
        rep = hex2(self.opcode) + ' '
        rep += ''.join(hex2(self.args[i]) + ' ' for i in range(self.addr_len)) + ''.join('   ' for i in range(2-self.addr_len)) 
        rep += ' '
        rep += self.op.upper()[:3] + ' '
        if self.addr_mode == 'imm':
            rep += '#$' + hex2(self.operand)
        elif self.addr_mode == 'zp':
            rep += '$' + hex2(self.addr)
        elif self.addr_mode == 'abs':
            rep += '$' + hex4(self.addr)
        elif self.addr_mode == 'rel':
            rep += '$' + hex4(self.operand)
        elif self.addr_mode == 'a':
            rep += 'A'
        elif self.addr_mode == 'ixid':
            rep += '($' + hex2(self.args[0]) + ',X) @ ' + hex2(self.addr)
        while len(rep) < 37:
            rep += ' '
        return rep

class Rom(object):
    '''class for reading in iNES files'''
    def __init__(self, f):
        self.f = f
        header = f.read(16)
        if header[:4] == 'NES\x1a':
            #print 'header constant OK!'
            pass
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
        self.prg_rom = map(lambda x: struct.unpack('B', x)[0], f.read(16384 * self.prg_size))
        self.chr_rom = f.read(8192 * self.chr_size)

filename = sys.argv[1]

rom = Rom(open(filename))
mach = Machine(rom)
#print hex(ord(mach.get_mem(mach.pc)))
mach.run()
