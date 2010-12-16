import sys
import struct
import cProfile

import pygame

def hex2(i):
    if i > 0xFF:
        print 'warning, printing larger than 0xff value with hex2'
        print hex(i)
    return '%02X' % (i & 0xFF)
def hex4(i):
    return '%04X' % (i & 0xFFFF)

colors = [
0x7C7C7C,
0x0000FC,
0x0000BC,
0x4428BC,
0x940084,
0xA80020,
0xA81000,
0x881400,
0x503000,
0x007800,
0x006800,
0x005800,
0x004058,
0x000000,
0x000000,
0x000000,
0xBCBCBC,
0x0078F8,
0x0058F8,
0x6844FC,
0xD800CC,
0xE40058,
0xF83800,
0xE45C10,
0xAC7C00,
0x00B800,
0x00A800,
0x00A844,
0x008888,
0x000000,
0x000000,
0x000000,
0xF8F8F8,
0x3CBCFC,
0x6888FC,
0x9878F8,
0xF878F8,
0xF85898,
0xF87858,
0xFCA044,
0xF8B800,
0xB8F818,
0x58D854,
0x58F898,
0x00E8D8,
0x787878,
0x000000,
0x000000,
0xFCFCFC,
0xA4E4FC,
0xB8B8F8,
0xD8B8F8,
0xF8B8F8,
0xF8A4C0,
0xF0D0B0,
0xFCE0A8,
0xF8D878,
0xD8F878,
0xB8F8B8,
0xB8F8D8,
0x00FCFC,
0xF8D8F8,
0x000000,
0x000000
]

keymap = {pygame.K_LEFT: 6,
    pygame.K_RIGHT: 7,
    pygame.K_UP: 4,
    pygame.K_DOWN: 5,
    pygame.K_x: 1,
    pygame.K_z: 0,
    pygame.K_RETURN: 3,
    pygame.K_s: 2}



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
    cycle_count = 0
#PPU
    sl = -1
    cyc = 0
    pctrl = 0
    pmask = 0
    pstat = 0b10100000
    oamaddr = 0
    p5 = 0
    p6 = 0
    scroll_x = scroll_y = 0
    platch = False
    paddr = 0
    taddr = 0
    xoff = 0
    fineX = 0
    pdata = 0
    ppu_mem = [0]
    ppu_mem_buf = 0
    ppu_cycles = 0
    frame_count = 0
    obj_mem = [0]
    nt_base = 0x2000
    at_base = 0x23c0
#input
    read_input_state = 8
    keys = [0] * 8

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
                ret = self.pstat
                self.pstat &= ~(1 << 7)
                self.platch = False
                return ret
            elif i == 4:
                ret = self.obj_mem[self.oamaddr]
                return ret
            elif i == 7:
                if self.paddr < 0x3f00:
                    res = self.ppu_mem_buf
                    self.ppu_mem_buf = self.ppu_get_mem(self.paddr)
                    print hex4(self.paddr)
                    self.paddr += 32 if self.pctrl & (1 << 2) else 1
                    self.paddr &= 0x3fff
                    return res
                else:
                    #needs to do some crap, also stil get mem
                    res = self.ppu_get_mem(self.paddr)
                    self.paddr += 32 if self.pctrl & (1 << 2) else 1
                    self.paddr &= 0x3fff
                    return res
        elif addr < 0x4018:
            if addr == 0x4016:
                if self.read_input_state < 8:
                    print 'reading input ', self.read_input_state,
                    print self.keys[self.read_input_state]
                    self.read_input_state += 1
                    return self.keys[self.read_input_state-1]
                else:
                    return 1
            return 0 # input ALU
        elif addr < 0x8000:
            return self.rom.prg_ram[addr-0x6000]
        elif addr < 0xC000 or self.rom.prg_size > 1:
            return self.rom.prg_rom[addr-0x8000]
        else:
            return self.rom.prg_rom[addr-0xC000]
    def set_mem(self, addr, val):
        if addr < 0x2000:
            self.mem[(addr) & 0x7ff] = val
        elif addr < 0x4000:
            i = (addr - 0x2000) & 0x7
            if i == 0:
                self.pctrl = val
                self.taddr &= (~(0x3 << 10))
                self.taddr |= (val & 0x3) << 10
            elif i == 1:
                self.pmask = val
            elif i == 3:
                self.oamaddr = val
            elif i == 4:
                self.obj_mem[self.oamaddr] = val
                self.oamaddr += 1
                self.oamaddr &= 0xff
            elif i == 5:
                if self.platch:
                    self.taddr &= (~0x73e0)
                    self.taddr |= (val >> 3) << 5
                    self.taddr |= (val & 0x7) << 12
                    self.platch = False
                else:
                    self.taddr &= ~0x1f
                    self.taddr |= val >> 3
                    self.xoff = val & 0x7
                    self.fineX = val & 0x7
                    self.platch = True
            elif i == 6:
                if self.platch:
                    self.taddr &= ~0xff
                    self.taddr |= val
                    self.paddr = self.taddr
                    self.platch = False
                else:
                    self.taddr &= 0xff
                    self.taddr |= (val & 0x3f) << 8
                    self.platch = True
            elif i == 7:
                self.ppu_set_mem(self.paddr, val)
                self.paddr += 32 if self.pctrl & (1 << 2) else 1
                self.paddr &= 0x3fff
        elif addr < 0x4018:
            if addr == 0x4016:
                if val & 1:
                    keys = pygame.key.get_pressed()
                    for keycode in keymap:
                        self.keys[keymap[keycode]] = 1 if keys[keycode] else 0
                self.read_input_state = 0
            elif addr == 0x4014:
                start = val << 8
                end = start + 0x100
                self.obj_mem = self.mem[start:end]

            pass # input / ALU
        elif addr < 0x8000:
            self.rom.prg_ram[addr-0x6000] = val
        else:
            pass

    def ppu_get_mem(self, addr):
        addr &= 0x3fff
        if addr < 0x2000:
            return self.rom.chr_rom[addr]
        elif addr < 0x3000:
            if not self.rom.flags6 & 1:
                #horizontal mirroring
                if addr < 0x2400:
                    return self.ppu_mem[addr]
                elif addr < 0x2800:
                    return self.ppu_mem[addr - 0x400]
                elif addr < 0x2C00:
                    return self.ppu_mem[addr]
                else:
                    return self.ppu_mem[addr - 0x400]
            else:
                #vertical mirroring
                if addr < 0x2800:
                    return self.ppu_mem[addr]
                else:
                    return self.ppu_mem[addr - 0x800]
 
        elif addr < 0x3f00:
            return self.ppu_get_mem(addr - 0x1000)
        else:
            #palette
            return self.ppu_mem[0x3f00 + (addr & 0x1f)]
    def ppu_set_mem(self, addr, val):
        addr &= 0x3fff
        if addr < 0x3000:
            if not self.rom.flags6 & 1:
                #horizontal mirroring
                if addr < 0x2400:
                    self.ppu_mem[addr] = val
                elif addr < 0x2800:
                    self.ppu_mem[addr - 0x400] = val
                elif addr < 0x2C00:
                    self.ppu_mem[addr] = val
                else:
                    self.ppu_mem[addr - 0x400] = val
            else:
                #vertical mirroring
                if addr < 0x2800:
                    self.ppu_mem[addr] = val
                else:
                    self.ppu_mem[addr - 0x800] = val
        elif addr < 0x3f00:
            self.ppu_set_mem(addr- 0x1000, val)
        else: 
            self.ppu_mem[0x3f00 + (addr & 0x1f)] = val


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
        res += ' VA:'+hex4(self.paddr)
        #res += ' CYC:%3i' % (self.cyc)
        #res += ' SL:%d' % self.sl
        return res

    def __init__(self, rom):
        self.rom = rom
        pygame.display.init()
        self.surface = pygame.display.set_mode((256,240))
        print self.surface.get_bitsize()
        self.pixels = pygame.surfarray.pixels2d(self.surface)
        self.mem = [0xff] * (0x800)
        #ppu stuff
        self.ppu_mem = [0xff] * (0x4000)
        self.obj_mem = [0xff] * (0x100)

    def run(self):
        self.reset()
        debug = True#False# True
        while True:
            if debug:
                print hex4(self.pc),
                print '',
            inst = self.next_inst()
            if debug:
                print inst,
                print '  ',
                print self.dump_regs()
            self.execute(inst)
            self.cycle_count += inst.cycles
            while self.ppu_cycles < self.cycle_count * 3:
                self.run_ppu()
                self.ppu_cycles += 1

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

    def run_ppu(self):
    #TODO sprites
    #TODO sprite 0 hit
    #TODO move vblank to end/make scanlines correct
        rendering_enabled = (self.pmask & (3 << 3))
        if self.sl < 0:
            if self.cyc == 341:
                self.pstat |= (1 << 7)
                if self.pctrl & (1 << 7):
                    self.push2(self.pc) #NMI
                    self.push(self.p)
                    self.pc = self.get_mem(0xfffa) + (self.get_mem(0xfffb) << 8)
        elif self.sl < 20:
            pass # vblank
        elif self.sl == 20:
            #start reading
            if rendering_enabled and self.cyc == 341:
                self.pstat &= ~(1 << 7)
                self.paddr = self.taddr
                self.fineX = self.xoff
                self.cyc = -1
                self.sl += 1
                print 'base' + hex4(self.paddr)
        else:
            if rendering_enabled and self.cyc < 256:
                x = self.cyc
                y = self.sl - 21
                self.fineX = (self.fineX + 1) & 0x7
                fineY = (self.paddr & 0x7000) >> 12
                if self.fineX == 0 and self.x < 256:
                    if self.paddr & 0x1f == 0x1f:
                        self.paddr = self.paddr + 0x400 - 0x1f
                    else:
                        self.paddr += 1
                # get new nt_byte
                nt_addr = 0x2000 + (self.paddr & 0xfff)
                self.at_base = (nt_addr & (~0xfff)) + 0x3c0
                self.nt_val = self.ppu_get_mem(nt_addr)
                base_pt_addr = 0x1000 if (self.pctrl & (1 << 4)) else 0
                self.pt_addr = (self.nt_val * 0x10) + base_pt_addr
                low = self.ppu_get_mem(self.pt_addr + fineY)
                hi = self.ppu_get_mem(self.pt_addr + 8 + fineY)
                low &= (1 << (7-self.fineX))
                low = 1 if low else 0
                hi &= (1 << (7-self.fineX))
                hi = 1 if hi else 0
                color_i = low | (hi << 1)
                #get new at value
                self.at = self.ppu_get_mem(self.at_base + ((nt_addr & 0x3ff)>>4))
                nt_off = (nt_addr & 0x3ff)
                row = (nt_off >> 6) & 1
                col = (nt_off & 0x2) >> 1
                at_val = self.at >> ((0 if row else 4) + (0 if col else 2))
                at_val &= 2
                at_val <<= 2
                color_i |= at_val
                if color_i & 3:
                    color = self.ppu_get_mem(0x3f00 + color_i)
                else:
                    color = self.ppu_get_mem(0x3f00)
                if x < 256:
                    if color < len(colors):
                        self.pixels[x,y] = colors[color]
        if self.cyc == 341:
            self.cyc = -1
            self.sl += 1
            if rendering_enabled and self.sl > 20:
                fineY = (self.paddr & 0x7000) >> 12
                if fineY == 7:
                    if self.paddr & 0x3ff >= 0x3c0:
                        self.paddr |= 0x800
                    else:
                        self.paddr += 0x20
                self.paddr &= ~0x1f
                self.paddr |= self.taddr & 0x1f
                self.paddr &= ~(1 << 10) 
                self.paddr |= self.taddr & (1 << 10)
                self.paddr &= ~(0x7000)
                self.paddr |= ((fineY+1) & 0x7) << 12
                self.fineX = self.xoff
        if self.sl == 260:
            self.sl = -1
            self.surface.unlock()
            pygame.display.flip()
            self.surface.fill(0x0)
            self.surface.lock()
            pygame.event.pump()
            print 'frame ', self.frame_count
            self.frame_count += 1
        self.cyc += 1


    def reset(self):
    #TODO what is the deal with SMB and megaman? loading probs
        self.s -= 3
        self.s &= 0xff
        self.mem = [0xff] * (0x800)
        self.mem[0x0008] = 0xf7
        self.mem[0x0009] = 0xef
        self.mem[0x000a] = 0xdf
        self.mem[0x000f] = 0xbf
        self.pc = self.get_mem(0xfffc) + (self.get_mem(0xfffd) << 8)

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

    def branch(self, bool, inst):
        if bool:
            inst.cycles += 1
            if inst.operand & 0xff00 != self.pc & 0xff00:
                inst.cycles += 1
            self.pc = inst.operand

    def bcs(self, inst):
        self.branch(self.get_flag('C'), inst)
    def bcc(self, inst):
        self.branch(not self.get_flag('C'), inst)
    def beq(self, inst):
        self.branch(self.get_flag('Z'), inst)
    def bne(self, inst):
        self.branch(not self.get_flag('Z'), inst)
    def bvs(self, inst):
        self.branch(self.get_flag('V'), inst)
    def bvc(self, inst):
        self.branch(not self.get_flag('V'), inst)
    def bpl(self, inst):
        self.branch(not self.get_flag('N'), inst)
    def bmi(self, inst):
        self.branch(self.get_flag('N'), inst)
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
    def cli(self, inst):
        self.set_flag('I', False)
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
        self.stored = self.a
        self.set_mem(inst.addr, self.a)
    def ldx(self, inst):
        self.x = inst.operand
        self.set_nz(self.x)
    def stx(self, inst):
        self.stored = self.x
        self.set_mem(inst.addr, self.x)
    def ldy(self, inst):
        self.y = inst.operand
        self.set_nz(self.y)
    def sty(self, inst):
        self.stored = self.y
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
#TODO brk, some illegals
    '''Class for parsing instructions'''
    opcodes = { 0x01 : ('ora', 'ixid', 6),
                0x03 : ('slo*', 'ixid', 1),
                0x04 : ('nop*', 'zp', 1),
                0x05 : ('ora', 'zp', 2),
                0x06 : ('asl', 'zp', 5),
                0x07 : ('slo*', 'zp', 1),
                0x08 : ('php', 'imp', 3),
                0x09 : ('ora', 'imm', 2),
                0x0a : ('asl_a', 'a', 2),
                0x0c : ('nop*', 'abs', 1),
                0x0d : ('ora', 'abs', 4),
                0x0e : ('asl', 'abs', 6),
                0x0f : ('slo*', 'abs', 1),
                0x10 : ('bpl', 'rel', 2),
                0x11 : ('ora', 'idix', 5),
                0x13 : ('slo*', 'idix', 1),
                0x14 : ('nop*', 'zpx', 1),
                0x15 : ('ora', 'zpx', 3),
                0x16 : ('asl', 'zpx', 6),
                0x17 : ('slo*', 'zpx', 1),
                0x18 : ('clc', 'imp', 2),
                0x19 : ('ora', 'absy', 4),
                0x1a : ('nop*', 'imp', 1),
                0x1b : ('slo*', 'absy', 1),
                0x1c : ('nop*', 'absx', 1),
                0x1d : ('ora', 'absx', 4),
                0x1e : ('asl', 'absx', 7),
                0x1f : ('slo*', 'absx', 1),
                0x20 : ('jsr', 'abs', 6),
                0x21 : ('and_', 'ixid', 6),
                0x23 : ('rla*', 'ixid', 1),
                0x24 : ('bit', 'zp', 3),
                0x25 : ('and_', 'zp', 2),
                0x26 : ('rol', 'zp', 5),
                0x27 : ('rla*', 'zp', 1),
                0x28 : ('plp', 'imp', 4),
                0x29 : ('and_', 'imm', 2),
                0x2a : ('rol_a', 'a', 2),
                0x2c : ('bit', 'abs', 4),
                0x2d : ('and_', 'abs', 4),
                0x2e : ('rol', 'abs', 6),
                0x2f : ('rla*', 'abs', 1),
                0x30 : ('bmi', 'rel', 2),
                0x31 : ('and_', 'idix', 5),
                0x33 : ('rla*', 'idix', 1),
                0x34 : ('nop*', 'zpx', 1),
                0x35 : ('and_', 'zpx', 3),
                0x36 : ('rol', 'zpx', 6),
                0x37 : ('rla*', 'zpx', 1),
                0x38 : ('sec', 'imp', 2),
                0x39 : ('and_', 'absy', 4),
                0x3a : ('nop*', 'imp', 1),
                0x3b : ('rla*', 'absy', 1),
                0x3c : ('nop*', 'absx', 1),
                0x3d : ('and_', 'absx', 4),
                0x3e : ('rol', 'absx', 7),
                0x3f : ('rla*', 'absx', 1),
                0x40 : ('rti', 'imp', 6),
                0x41 : ('eor', 'ixid', 6),
                0x43 : ('sre*', 'ixid', 1),
                0x44 : ('nop*', 'zp', 1),
                0x45 : ('eor', 'zp', 3),
                0x46 : ('lsr', 'zp', 5),
                0x47 : ('sre*', 'zp', 1),
                0x48 : ('pha', 'imp', 3),
                0x49 : ('eor', 'imm', 2),
                0x4a : ('lsr_a', 'a', 2),
                0x4c : ('jmp', 'abs', 3),
                0x4d : ('eor', 'abs', 4),
                0x4e : ('lsr', 'abs', 6),
                0x4f : ('sre*', 'abs', 1),
                0x50 : ('bvc', 'rel', 2),
                0x51 : ('eor', 'idix', 5),
                0x53 : ('sre*', 'idix', 1),
                0x54 : ('nop*', 'zpx', 1),
                0x55 : ('eor', 'zpx', 4),
                0x56 : ('lsr', 'zpx', 6),
                0x57 : ('sre*', 'zpx', 1),
                0x58 : ('cli', 'imp', 2),
                0x59 : ('eor', 'absy', 4),
                0x5a : ('nop*', 'imp', 1),
                0x5b : ('sre*', 'absy', 1),
                0x5c : ('nop*', 'absx', 1),
                0x5d : ('eor', 'absx', 4),
                0x5e : ('lsr', 'absx', 7),
                0x5f : ('sre*', 'absx', 1),
                0x60 : ('rts', 'imp', 6),
                0x61 : ('adc', 'ixid', 6),
                0x63 : ('rra*', 'ixid', 1),
                0x64 : ('nop*', 'zp', 1),
                0x65 : ('adc', 'zp', 3),
                0x66 : ('ror', 'zp', 5),
                0x67 : ('rra*', 'zp', 1),
                0x68 : ('pla', 'imp', 4),
                0x69 : ('adc', 'imm', 2),
                0x6a : ('ror_a', 'a', 2),
                0x6c : ('jmp', 'absi', 5),
                0x6d : ('adc', 'abs', 4),
                0x6e : ('ror', 'abs', 6),
                0x6f : ('rra*', 'abs', 1),
                0x70 : ('bvs', 'rel', 2),
                0x71 : ('adc', 'idix', 5),
                0x73 : ('rra*', 'idix', 1),
                0x74 : ('nop*', 'zpx', 1),
                0x75 : ('adc', 'zpx', 4),
                0x76 : ('ror', 'zpx', 6),
                0x77 : ('rra*', 'zpx', 1),
                0x78 : ('sei', 'imp', 2),
                0x79 : ('adc', 'absy', 4),
                0x7a : ('nop*', 'imp', 1),
                0x7b : ('rra*', 'absy', 1),
                0x7c : ('nop*', 'absx', 1),
                0x7d : ('adc', 'absx', 4),
                0x7e : ('ror', 'absx', 7),
                0x7f : ('rra*', 'absx', 1),
                0x80 : ('nop*', 'imm', 1),
                0x81 : ('sta', 'ixid', 6),
                0x83 : ('sax*', 'ixid', 1),
                0x84 : ('sty', 'zp', 3),
                0x85 : ('sta', 'zp', 3),
                0x86 : ('stx', 'zp', 3),
                0x87 : ('sax*', 'zp', 1),
                0x88 : ('dey', 'imp', 2),
                0x8a : ('txa', 'imp', 2),
                0x8c : ('sty', 'abs', 4),
                0x8d : ('sta', 'abs', 4),
                0x8e : ('stx', 'abs', 4),
                0x8f : ('sax*', 'abs', 1),
                0x90 : ('bcc', 'rel', 2),
                0x91 : ('sta', 'idix', 6),
                0x94 : ('sty', 'zpx', 4),
                0x95 : ('sta', 'zpx', 4),
                0x96 : ('stx', 'zpy', 4),
                0x97 : ('sax*', 'zpy', 1),
                0x98 : ('tya', 'imp', 2),
                0x99 : ('sta', 'absy', 5),
                0x9a : ('txs', 'imp', 2),
                0x9d : ('sta', 'absx', 5),
                0xa0 : ('ldy', 'imm', 2),
                0xa1 : ('lda', 'ixid', 6),
                0xa2 : ('ldx', 'imm', 2),
                0xa3 : ('lax*', 'ixid', 1),
                0xa4 : ('ldy', 'zp', 3),
                0xa5 : ('lda', 'zp', 3),
                0xa6 : ('ldx', 'zp', 3),
                0xa7 : ('lax*', 'zp', 1),
                0xa8 : ('tay', 'imp', 2),
                0xa9 : ('lda', 'imm', 2),
                0xaa : ('tax', 'imp', 2),
                0xac : ('ldy', 'abs', 4),
                0xad : ('lda', 'abs', 4),
                0xae : ('ldx', 'abs', 4),
                0xaf : ('lax*', 'abs', 1),
                0xb0 : ('bcs', 'rel', 2),
                0xb1 : ('lda', 'idix', 5),
                0xb3 : ('lax*', 'idix', 1),
                0xb4 : ('ldy', 'zpx', 4),
                0xb5 : ('lda', 'zpx', 4),
                0xb6 : ('ldx', 'zpy', 4),
                0xb7 : ('lax*', 'zpy', 1),
                0xb8 : ('clv', 'imp', 2),
                0xb9 : ('lda', 'absy', 4),
                0xba : ('tsx', 'imp', 2),
                0xbc : ('ldy', 'absx', 4),
                0xbd : ('lda', 'absx', 4),
                0xbe : ('ldx', 'absy', 4),
                0xbf : ('lax*', 'absy', 1),
                0xc0 : ('cpy', 'imm', 2),
                0xc1 : ('cmp', 'ixid', 6),
                0xc3 : ('dcp*', 'ixid', 1),
                0xc4 : ('cpy', 'zp', 3),
                0xc5 : ('cmp', 'zp', 3),
                0xc6 : ('dec', 'zp', 5),
                0xc7 : ('dcp*', 'zp', 1),
                0xc8 : ('iny', 'imp', 2),
                0xc9 : ('cmp', 'imm', 2),
                0xca : ('dex', 'imp', 2),
                0xcc : ('cpy', 'abs', 4),
                0xcd : ('cmp', 'abs', 4),
                0xce : ('dec', 'abs', 6),
                0xcf : ('dcp*', 'abs', 1),
                0xd0 : ('bne', 'rel', 2),
                0xd1 : ('cmp', 'idix', 5),
                0xd3 : ('dcp*', 'idix', 1),
                0xd4 : ('nop*', 'zpx', 1),
                0xd5 : ('cmp', 'zpx', 4),
                0xd6 : ('dec', 'zpx', 6),
                0xd7 : ('dcp*', 'zpx', 1),
                0xd8 : ('cld', 'imp', 2),
                0xd9 : ('cmp', 'absy', 4),
                0xda : ('nop*', 'imp', 1),
                0xdb : ('dcp*', 'absy', 1),
                0xdc : ('nop*', 'absx', 1),
                0xdd : ('cmp', 'absx', 4),
                0xde : ('dec', 'absx', 7),
                0xdf : ('dcp*', 'absx', 1),
                0xe0 : ('cpx', 'imm', 2),
                0xe1 : ('sbc', 'ixid', 6),
                0xe3 : ('isb*', 'ixid', 1),
                0xe4 : ('cpx', 'zp', 3),
                0xe5 : ('sbc', 'zp', 3),
                0xe6 : ('inc', 'zp', 5),
                0xe7 : ('isb*', 'zp', 1),
                0xe8 : ('inx', 'imp', 2),
                0xe9 : ('sbc', 'imm', 2),
                0xea : ('nop', 'imp', 2),
                0xeb : ('sbc*', 'imm', 1),
                0xec : ('cpx', 'abs', 4),
                0xed : ('sbc', 'abs', 4),
                0xee : ('inc', 'abs', 6),
                0xef : ('isb*', 'abs', 1),
                0xf0 : ('beq', 'rel', 2),
                0xf1 : ('sbc', 'idix', 5),
                0xf3 : ('isb*', 'idix', 1),
                0xf4 : ('nop*', 'zpx', 1),
                0xf5 : ('sbc', 'zpx', 4),
                0xf6 : ('inc', 'zpx', 6),
                0xf7 : ('isb*', 'zpx', 1),
                0xf8 : ('sed', 'imp', 2),
                0xf9 : ('sbc', 'absy', 4),
                0xfa : ('nop*', 'imp', 1),
                0xfb : ('isb*', 'absy', 1),
                0xfc : ('nop*', 'absx', 1),
                0xfd : ('sbc', 'absx', 4),
                0xfe : ('inc', 'absx', 7),
                0xff : ('isb*', 'absx', 7)}
    type = 'nop'
    opcode = 0x00 
    addr_mode = ''
    operand = 0
    def __init__(self, op):
        self.opcode = op
        self.illegal = False
        try:
            self.op, self.addr_mode, self.cycles = self.opcodes[op]
            if self.op[-1:] == '*':
                self.op = self.op [:-1]
                self.illegal = True
        except:
            print 'unsupported opcode: ' + hex2(op)
            sys.exit(1)
        self.addr_len = 0
    def parse_operand(self, addr, mach):
        #TODO fix horrible don't read on 'st' hack
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
            if self.op[:2] != 'st':
                self.operand = mach.get_mem(self.addr)
            self.addr_len = 1
        elif self.addr_mode == 'abs':
            self.addr = addr[0] + (addr[1] << 8)
            if self.op[:2] != 'st':
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
            if self.op[:2] != 'st':
                self.operand = mach.get_mem(self.addr)
            self.addr_len = 2
            if self.i_addr & 0xff00 != self.addr & 0xff00:
                self.cycles += 1
        elif self.addr_mode == 'absx':
            self.i_addr = addr[0] + (addr[1] << 8)
            self.addr = (self.i_addr + mach.x) & 0xffff
            if self.op[:2] != 'st':
                self.operand = mach.get_mem(self.addr)
            self.addr_len = 2
            if self.i_addr & 0xff00 != self.addr & 0xff00:
                self.cycles += 1
        elif self.addr_mode == 'rel':
            off = addr[0] if addr[0] < 0x80 else addr[0] - 0x100
            self.operand = (off + mach.pc + 1) 
            self.addr_len = 1
        elif self.addr_mode == 'ixid':
            self.i_addr = (addr[0] + mach.x) & 0xff
            self.addr = (mach.get_mem(self.i_addr) + 
                    (mach.get_mem((self.i_addr+1) & 0xff) << 8))
            if self.op[:2] != 'st':
                self.operand = mach.get_mem(self.addr)
            self.addr_len = 1
        elif self.addr_mode == 'idix':
            self.i_addr = addr[0]
            self.addr = (mach.get_mem(self.i_addr) +
                    (mach.get_mem((self.i_addr+1) & 0xff) << 8)) + mach.y
            self.addr &= 0xffff
            if self.op[:2] != 'st':
                self.operand = mach.get_mem(self.addr)
            self.addr_len = 1
            if self.addr & 0xff00 != (self.addr - mach.y) & 0xff00:
                self.cycles += 1
        elif self.addr_mode == 'zpx':
            self.i_addr = addr[0]
            self.addr = (self.i_addr + mach.x) & 0xff
            if self.op[:2] != 'st':
                self.operand = mach.get_mem(self.addr)
            self.addr_len = 1
        elif self.addr_mode == 'zpy':
            self.i_addr = addr[0]
            self.addr = (self.i_addr + mach.y) & 0xff
            if self.op[:2] != 'st':
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
        self.prg_rom = map(lambda x: struct.unpack('B', x)[0], f.read(16384 * self.prg_size))
        print self.prg_size
        print hex4(len(self.prg_rom))
        self.chr_ram = (self.chr_size == 0)
        if self.chr_ram:
            self.chr_rom = [0xff] * 8192
        else:
            self.chr_rom = map(lambda x: struct.unpack('B', x)[0], f.read(8192 * self.chr_size))
        self.prg_ram = [0xff] * (8192 * 1 if not self.prg_ram_size else self.prg_ram_size)


filename = sys.argv[1]
rom = Rom(open(filename))
mach = Machine(rom)
#cProfile.run('mach.run()')
mach.run()
