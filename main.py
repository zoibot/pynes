import sys
import struct

import pygame

def hex2(i):
    if i > 0xFF:
        print 'warning, printing larger than 0xff value with hex2'
        print hex(i)
    return '%02X' % (i & 0xFF)
def hex4(i):
    return '%04X' % (i & 0xFFFF)

class Machine(object):
    '''Class for actually simulating the machine'''
#CPU
    pc = 0x8000 # for nestest
    prev_pc = pc
    a = 0
    s = 0
    p = 0x24
    x = y = 0
    mem = [0]
#PPU
    sl = -1
    cyc = 0
    pctrl = 0
    pmask = 0
    pstat = 0b10100000
    p3 = 0
    p5 = 0
    p6 = 0
    pscroll = 0
    paddr = 0
    paddr_state = False # false/true-> waiting for low/hi byte
    pdata = 0
    ppu_mem = [0]

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
        if addr < 0x2000:
            return self.mem[(addr) & 0x7ff]
        elif addr < 0x4000:
            #ppu
            i = (addr - 0x2000) & 0x7
            if i == 0:
                pass
            elif i == 2:
                return self.pstat
        elif addr < 0x4018:
            pass # input / ALU
        elif addr < 0x8000:
            pass
        elif addr < 0xC000:
            return self.rom.prg_rom[addr-0x8000]
        else:
            return self.rom.prg_rom[addr-0xC000]
    def set_mem(self, addr, val):
        if addr < 0x2000:
            self.mem[(addr) & 0x7ff] = val
        elif addr < 0x4000:
            i = (addr - 0x2000) & 0x7
            if i == 0:
                pass
            elif i == 6:
                if self.paddr_state:
                    self.paddr |= (val << 8)
                else:
                    self.paddr = val
                paddr_state = not paddr_state
            #ppu
        elif addr < 0x4018:
            pass # input / ALU
        else:
            pass

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
        pygame.display.init()
        self.surface = pygame.display.set_mode((256,240))
        self.mem = [0xff] * (0x800)
        #ppu stuff

    def run(self):
        #TODO interrupts
        self.reset()
        debug = True
        while True:
            if debug:
                print hex4(self.pc),
                print '',
            try:
                inst = self.next_inst()
            except:
                print 'Done!'
                break
            if debug:
                print inst,
                print '  ',
                print self.dump_regs()
            self.execute(inst)

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
        self.mem = [0xff] * (0x800)
        self.mem[0x0008] = 0xf7
        self.mem[0x0009] = 0xef
        self.mem[0x000a] = 0xdf
        self.mem[0x000f] = 0xbf
        self.pc = self.get_mem(0xfffc) + (self.get_mem(0xfffd) << 8)
        #ppu stuff

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
        m = self.get_mem(inst.addr)
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
        self.set_mem(inst.addr, self.a)
    def ldx(self, inst):
        self.x = inst.operand
        self.set_nz(self.x)
    def stx(self, inst):
        self.set_mem(inst.addr, self.x)
    def ldy(self, inst):
        self.y = inst.operand
        self.set_nz(self.y)
    def sty(self, inst):
        self.set_mem(inst.addr, self.y)
    def lax(self, inst):
        self.a = inst.operand
        self.x = inst.operand
        self.set_nz(self.a)
    def sax(self, inst):
        self.set_mem(inst.addr, self.a & self.x)

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
        self.set_flag('C', old_a >= inst.operand)
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
    def inc(self, inst):
        inst.operand += 1
        inst.operand &= 0xff
        self.set_nz(inst.operand)
        self.set_mem(inst.addr, inst.operand)
    def dec(self, inst):
        inst.operand -= 1
        inst.operand &= 0xff
        self.set_nz(inst.operand)
        self.set_mem(inst.addr, inst.operand)
    def dcp(self, inst):
        self.set_mem(inst.addr, (inst.operand - 1) & 0xff)
        self.compare(self.a, (inst.operand - 1) & 0xff)
    def isb(self, inst):
        inst.operand = (inst.operand + 1) & 0xff
        self.set_mem(inst.addr, inst.operand)
        self.sbc(inst)

    def lsr_a(self, inst):
        self.set_flag('C', self.a & (1))
        self.a >>= 1
        self.set_nz(self.a)
    def lsr(self, inst):
        self.set_flag('C', inst.operand & (1))
        inst.operand >>= 1
        self.set_mem(inst.addr, inst.operand)
        self.set_nz(inst.operand)
    def asl_a(self, inst):
        self.set_flag('C', self.a & (1 << 7))
        self.a <<= 1
        self.a &= 0xff
        self.set_nz(self.a)
    def asl(self, inst):
        self.set_flag('C', inst.operand & (1 << 7))
        inst.operand <<= 1
        inst.operand &= 0xff
        self.set_mem(inst.addr, inst.operand)
        self.set_nz(inst.operand)
    def ror_a(self, inst):
        new_c = self.a & 1
        self.a >>= 1
        self.a |= (1 << 7) if self.get_flag('C') else 0
        self.set_flag('C', new_c)
        self.set_nz(self.a)
    def ror(self, inst):
        new_c = inst.operand & 1
        inst.operand >>= 1
        inst.operand |= (1 << 7) if self.get_flag('C') else 0
        self.set_flag('C', new_c)
        self.set_mem(inst.addr, inst.operand)
        self.set_nz(inst.operand)
    def rol_a(self, inst):
        new_c = self.a & (1 << 7)
        self.a <<= 1
        self.a |= 1 if self.get_flag('C') else 0
        self.a &= 0xff
        self.set_flag('C', new_c)
        self.set_nz(self.a)
    def rol(self, inst):
        new_c = inst.operand & (1 << 7)
        inst.operand <<= 1
        inst.operand |= 1 if self.get_flag('C') else 0
        inst.operand &= 0xff
        self.set_flag('C', new_c)
        self.set_mem(inst.addr, inst.operand)
        self.set_nz(inst.operand)
    def slo(self, inst):
        self.asl(inst)
        self.ora(inst)
    def rla(self, inst):
        self.rol(inst)
        self.and_(inst)
    def sre(self, inst):
        self.lsr(inst)
        self.eor(inst)
    def rra(self, inst):
        self.ror(inst)
        self.adc(inst)
    
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
    opcodes = { 0x01 : ('ora', 'ixid'),
                0x03 : ('slo*', 'ixid'),
                0x04 : ('nop*', 'zp'),
                0x05 : ('ora', 'zp'),
                0x06 : ('asl', 'zp'),
                0x07 : ('slo*', 'zp'),
                0x08 : ('php', 'imp'),
                0x09 : ('ora', 'imm'),
                0x0a : ('asl_a', 'a'),
                0x0c : ('nop*', 'abs'),
                0x0d : ('ora', 'abs'),
                0x0e : ('asl', 'abs'),
                0x0f : ('slo*', 'abs'),
                0x10 : ('bpl', 'rel'),
                0x11 : ('ora', 'idix'),
                0x13 : ('slo*', 'idix'),
                0x14 : ('nop*', 'zpx'),
                0x15 : ('ora', 'zpx'),
                0x16 : ('asl', 'zpx'),
                0x17 : ('slo*', 'zpx'),
                0x18 : ('clc', 'imp'),
                0x19 : ('ora', 'absy'),
                0x1a : ('nop*', 'imp'),
                0x1b : ('slo*', 'absy'),
                0x1c : ('nop*', 'absx'),
                0x1d : ('ora', 'absx'),
                0x1e : ('asl', 'absx'),
                0x1f : ('slo*', 'absx'),
                0x20 : ('jsr', 'abs'),
                0x21 : ('and_', 'ixid'),
                0x23 : ('rla*', 'ixid'),
                0x24 : ('bit', 'zp'),
                0x25 : ('and_', 'zp'),
                0x26 : ('rol', 'zp'),
                0x27 : ('rla*', 'zp'),
                0x28 : ('plp', 'imp'),
                0x29 : ('and_', 'imm'),
                0x2a : ('rol_a', 'a'),
                0x2c : ('bit', 'abs'),
                0x2d : ('and_', 'abs'),
                0x2e : ('rol', 'abs'),
                0x2f : ('rla*', 'abs'),
                0x30 : ('bmi', 'rel'),
                0x31 : ('and_', 'idix'),
                0x33 : ('rla*', 'idix'),
                0x34 : ('nop*', 'zpx'),
                0x35 : ('and_', 'zpx'),
                0x36 : ('rol', 'zpx'),
                0x37 : ('rla*', 'zpx'),
                0x38 : ('sec', 'imp'),
                0x39 : ('and_', 'absy'),
                0x3a : ('nop*', 'imp'),
                0x3b : ('rla*', 'absy'),
                0x3c : ('nop*', 'absx'),
                0x3d : ('and_', 'absx'),
                0x3e : ('rol', 'absx'),
                0x3f : ('rla*', 'absx'),
                0x40 : ('rti', 'imp'),
                0x41 : ('eor', 'ixid'),
                0x43 : ('sre*', 'ixid'),
                0x44 : ('nop*', 'zp'),
                0x45 : ('eor', 'zp'),
                0x46 : ('lsr', 'zp'),
                0x47 : ('sre*', 'zp'),
                0x48 : ('pha', 'imp'),
                0x49 : ('eor', 'imm'),
                0x4a : ('lsr_a', 'a'),
                0x4c : ('jmp', 'abs'),
                0x4d : ('eor', 'abs'),
                0x4e : ('lsr', 'abs'),
                0x4f : ('sre*', 'abs'),
                0x50 : ('bvc', 'rel'),
                0x51 : ('eor', 'idix'),
                0x53 : ('sre*', 'idix'),
                0x54 : ('nop*', 'zpx'),
                0x55 : ('eor', 'zpx'),
                0x56 : ('lsr', 'zpx'),
                0x57 : ('sre*', 'zpx'),
                0x59 : ('eor', 'absy'),
                0x5a : ('nop*', 'imp'),
                0x5b : ('sre*', 'absy'),
                0x5c : ('nop*', 'absx'),
                0x5d : ('eor', 'absx'),
                0x5e : ('lsr', 'absx'),
                0x5f : ('sre*', 'absx'),
                0x60 : ('rts', 'imp'),
                0x61 : ('adc', 'ixid'),
                0x63 : ('rra*', 'ixid'),
                0x64 : ('nop*', 'zp'),
                0x65 : ('adc', 'zp'),
                0x66 : ('ror', 'zp'),
                0x67 : ('rra*', 'zp'),
                0x68 : ('pla', 'imp'),
                0x69 : ('adc', 'imm'),
                0x6a : ('ror_a', 'a'),
                0x6c : ('jmp', 'absi'),
                0x6d : ('adc', 'abs'),
                0x6e : ('ror', 'abs'),
                0x6f : ('rra*', 'abs'),
                0x70 : ('bvs', 'rel'),
                0x71 : ('adc', 'idix'),
                0x73 : ('rra*', 'idix'),
                0x74 : ('nop*', 'zpx'),
                0x75 : ('adc', 'zpx'),
                0x76 : ('ror', 'zpx'),
                0x77 : ('rra*', 'zpx'),
                0x78 : ('sei', 'imp'),
                0x79 : ('adc', 'absy'),
                0x7a : ('nop*', 'imp'),
                0x7b : ('rra*', 'absy'),
                0x7c : ('nop*', 'absx'),
                0x7d : ('adc', 'absx'),
                0x7e : ('ror', 'absx'),
                0x7f : ('rra*', 'absx'),
                0x80 : ('nop*', 'imm'),
                0x81 : ('sta', 'ixid'),
                0x83 : ('sax*', 'ixid'),
                0x84 : ('sty', 'zp'),
                0x85 : ('sta', 'zp'),
                0x86 : ('stx', 'zp'),
                0x87 : ('sax*', 'zp'),
                0x88 : ('dey', 'imp'),
                0x8a : ('txa', 'imp'),
                0x8c : ('sty', 'abs'),
                0x8d : ('sta', 'abs'),
                0x8e : ('stx', 'abs'),
                0x8f : ('sax*', 'abs'),
                0x90 : ('bcc', 'rel'),
                0x91 : ('sta', 'idix'),
                0x94 : ('sty', 'zpx'),
                0x95 : ('sta', 'zpx'),
                0x96 : ('stx', 'zpy'),
                0x97 : ('sax*', 'zpy'),
                0x98 : ('tya', 'imp'),
                0x99 : ('sta', 'absy'),
                0x9a : ('txs', 'imp'),
                0x9d : ('sta', 'absx'),
                0xa0 : ('ldy', 'imm'),
                0xa1 : ('lda', 'ixid'),
                0xa2 : ('ldx', 'imm'),
                0xa3 : ('lax*', 'ixid'),
                0xa4 : ('ldy', 'zp'),
                0xa5 : ('lda', 'zp'),
                0xa6 : ('ldx', 'zp'),
                0xa7 : ('lax*', 'zp'),
                0xa8 : ('tay', 'imp'),
                0xa9 : ('lda', 'imm'),
                0xaa : ('tax', 'imp'),
                0xac : ('ldy', 'abs'),
                0xad : ('lda', 'abs'),
                0xae : ('ldx', 'abs'),
                0xaf : ('lax*', 'abs'),
                0xb0 : ('bcs', 'rel'),
                0xb1 : ('lda', 'idix'),
                0xb3 : ('lax*', 'idix'),
                0xb4 : ('ldy', 'zpx'),
                0xb5 : ('lda', 'zpx'),
                0xb6 : ('ldx', 'zpy'),
                0xb7 : ('lax*', 'zpy'),
                0xb8 : ('clv', 'imp'),
                0xb9 : ('lda', 'absy'),
                0xba : ('tsx', 'imp'),
                0xbc : ('ldy', 'absx'),
                0xbd : ('lda', 'absx'),
                0xbe : ('ldx', 'absy'),
                0xbf : ('lax*', 'absy'),
                0xc0 : ('cpy', 'imm'),
                0xc1 : ('cmp', 'ixid'),
                0xc3 : ('dcp*', 'ixid'),
                0xc4 : ('cpy', 'zp'),
                0xc5 : ('cmp', 'zp'),
                0xc6 : ('dec', 'zp'),
                0xc7 : ('dcp*', 'zp'),
                0xc8 : ('iny', 'imp'),
                0xc9 : ('cmp', 'imm'),
                0xca : ('dex', 'imp'),
                0xcc : ('cpy', 'abs'),
                0xcd : ('cmp', 'abs'),
                0xce : ('dec', 'abs'),
                0xcf : ('dcp*', 'abs'),
                0xd0 : ('bne', 'rel'),
                0xd1 : ('cmp', 'idix'),
                0xd3 : ('dcp*', 'idix'),
                0xd4 : ('nop*', 'zpx'),
                0xd5 : ('cmp', 'zpx'),
                0xd6 : ('dec', 'zpx'),
                0xd7 : ('dcp*', 'zpx'),
                0xd8 : ('cld', 'imp'),
                0xd9 : ('cmp', 'absy'),
                0xda : ('nop*', 'imp'),
                0xdb : ('dcp*', 'absy'),
                0xdc : ('nop*', 'absx'),
                0xdd : ('cmp', 'absx'),
                0xde : ('dec', 'absx'),
                0xdf : ('dcp*', 'absx'),
                0xe0 : ('cpx', 'imm'),
                0xe1 : ('sbc', 'ixid'),
                0xe3 : ('isb*', 'ixid'),
                0xe4 : ('cpx', 'zp'),
                0xe5 : ('sbc', 'zp'),
                0xe6 : ('inc', 'zp'),
                0xe7 : ('isb*', 'zp'),
                0xe8 : ('inx', 'imp'),
                0xe9 : ('sbc', 'imm'),
                0xea : ('nop', 'imp'),
                0xeb : ('sbc*', 'imm'),
                0xec : ('cpx', 'abs'),
                0xed : ('sbc', 'abs'),
                0xee : ('inc', 'abs'),
                0xef : ('isb*', 'abs'),
                0xf0 : ('beq', 'rel'),
                0xf1 : ('sbc', 'idix'),
                0xf3 : ('isb*', 'idix'),
                0xf4 : ('nop*', 'zpx'),
                0xf5 : ('sbc', 'zpx'),
                0xf6 : ('inc', 'zpx'),
                0xf7 : ('isb*', 'zpx'),
                0xf8 : ('sed', 'imp'),
                0xf9 : ('sbc', 'absy'),
                0xfa : ('nop*', 'imp'),
                0xfb : ('isb*', 'absy'),
                0xfc : ('nop*', 'absx'),
                0xfd : ('sbc', 'absx'),
                0xfe : ('inc', 'absx'),
                0xff : ('isb*', 'absx'),}
    type = 'nop'
    opcode = 0x00 
    addr_mode = ''
    operand = 0
    def __init__(self, op):
        self.opcode = op
        self.illegal = False
        try:
            self.op, self.addr_mode = self.opcodes[op]
            if self.op[-1:] == '*':
                self.op = self.op [:-1]
                self.illegal = True
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
        elif self.addr_mode == 'absi':
            self.i_addr = addr[0] + (addr[1] << 8)
            self.addr = (mach.get_mem(self.i_addr) 
                    + (mach.get_mem(((self.i_addr+1) & 0xff) 
                        + (self.i_addr & 0xff00)) << 8))
            self.addr_len = 2
        elif self.addr_mode == 'absy':
            self.i_addr = addr[0] + (addr[1] << 8)
            self.addr = (self.i_addr + mach.y) & 0xffff
            self.operand = mach.get_mem(self.addr)
            self.addr_len = 2
        elif self.addr_mode == 'absx':
            self.i_addr = addr[0] + (addr[1] << 8)
            self.addr = (self.i_addr + mach.x) & 0xffff
            self.operand = mach.get_mem(self.addr)
            self.addr_len = 2
        elif self.addr_mode == 'rel':
            off = addr[0] if addr[0] < 0x80 else addr[0] - 0x100
            self.operand = (off + mach.pc + 1) 
            self.addr_len = 1
        elif self.addr_mode == 'ixid':
            #TODO these 0xff are suspect, possibly 0xffff?
            self.i_addr = (addr[0] + mach.x) & 0xff
            self.addr = (mach.get_mem(self.i_addr) + 
                    (mach.get_mem((self.i_addr+1) & 0xff) << 8))
            self.operand = mach.get_mem(self.addr)
            self.addr_len = 1
        elif self.addr_mode == 'idix':
            self.i_addr = addr[0]
            self.addr = (mach.get_mem(self.i_addr) +
                    (mach.get_mem((self.i_addr+1) & 0xff) << 8)) + mach.y
            self.addr &= 0xffff
            self.operand = mach.get_mem(self.addr)
            self.addr_len = 1
        elif self.addr_mode == 'zpx':
            self.i_addr = addr[0]
            self.addr = (self.i_addr + mach.x) & 0xff
            self.operand = mach.get_mem(self.addr)
            self.addr_len = 1
        elif self.addr_mode == 'zpy':
            self.i_addr = addr[0]
            self.addr = (self.i_addr + mach.y) & 0xff
            self.operand = mach.get_mem(self.addr)
            self.addr_len = 1
        else:
            print 'Error, unrecognized addressing mode'
            sys.exit(1)
    def __repr__(self):
        #TODO rewrite
        rep = ''
        rep += hex2(self.opcode) + ' '
        rep += ''.join(hex2(self.args[i]) + ' ' for i in range(self.addr_len)) + ''.join('   ' for i in range(2-self.addr_len)) 
        if self.illegal:
            rep += '*'
        else:
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
            rep += '($' + hex2(self.args[0]) + ',X) @ ' + hex2(self.i_addr)
        elif self.addr_mode == 'idix':
            #man this is so weird
            rep += '($' + hex2(self.args[0]) + '),Y     ' + hex2((self.addr-mach.y)&0xff) + ' @ ' + hex2((self.addr) >> 8)
        elif self.addr_mode == 'absi':
            rep += '($' + hex4(self.i_addr) + ')'
            rep += '     ' + hex2(self.addr & 0xff)
        elif self.addr_mode == 'absy':
            rep += '$'+hex4(self.i_addr)+',Y @ '+hex4(self.addr)
        elif self.addr_mode == 'absx':
            rep += '$'+hex4(self.i_addr)+',X @ '+hex4(self.addr)
        elif self.addr_mode == 'zpx':
            rep += '$'+hex2(self.i_addr)+',X @ '+hex2(self.addr)
        elif self.addr_mode == 'zpy':
            rep += '$'+hex2(self.i_addr)+',Y @ '+hex2(self.addr)
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
        print self.prg_size
        self.prg_rom = map(lambda x: struct.unpack('B', x)[0], f.read(16384 * self.prg_size))
        self.chr_rom = f.read(8192 * self.chr_size)

filename = sys.argv[1]

rom = Rom(open(filename))
mach = Machine(rom)
#print hex(ord(mach.get_mem(mach.pc)))
mach.run()
