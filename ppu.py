from util import *

class Sprite(object):
    def __init__(self, index):
        self.index = index
    def update(self, data):
        self.y = data[0]
        self.tile = data[1]
        self.attrs = data[2]
        self.x = data[3]

class NameTable(object):
    name = 'hi'
    width = 32
    height = 32

    def __init__(self, num):
        self.name = 'Nt' + str(num)
        self.tile = array.array('B')
        self.tile.fromlist([0xff]*(self.width*self.height))
        self.attrib = array.array('B')
        self.attrib.fromlist([0xff]*(self.width*self.height))

    def get_byte(self, x, y):
        return self.tile[y*self.width+x]

    def write_byte(self, offset, val):
        self.tile[offset] = val

    def get_attrib(self, x, y):
        return self.tile[y*self.width+x]

    def write_attrib(self, ix, val):
        basex = (index & 7) << 2
        basey = (index >> 3) << 2
        for yy in range(2):
            for xx in range(2):
                att = (val >> (2 * (yy*2+xx))) & 3
                    for y in range(2):
                        for x in range(2):
                            tiley, tilex = basex+xx*2+x, basy+yy*2+y
                            self.attrib[tiley*self.width+tilex] = att << 2



class PatternTables(object):
    patterns = None
    def __init__(self):
        self.patterns = {}

    def update_all(self):
        for i in xrange(0,0x2000,16):
            self.update_pattern(i)

    def update(self, addr):
        for y in xrange(8):
            lo = self.nes.rom.chr_rom[addr + y]
            hi = self.nes.rom.chr_rom[addr + y + 8]
            self.patterns[addr,y] = [((lo >> (7-x)) & 1) | (((hi >> (7-x)) & 1) << 1) for x in xrange(8)] 

class Palette(object):
    #TODO grayscale
    bg_palette = None
    spr_palette = None
    ppu = None
    def __init__(self, ppu):
        bg_palette = array('I')
        bg_palette.fromlist([0]*16)
        spr_palette = array('I')
        spr_palette.fromlist([0]*16)
        self.ppu = ppu
    def update(self):
        for i in range(16):
            self.bg_palette[i] = colors[self.ppu.ppu_mem[0x3f00+i] & 63]
        for i in range(16):
            self.spr_palette[i] = colors[self.ppu.ppu_mem[0x3f10+i] & 63]
        

class PPU(object):
    nes = None

    cycles = 0

    #memory stuff
    ppu_mem = None
    ppu_mem_buf = 0
    mirror_table = None
    platch = False
    obj_mem = None
    obj_addr = 0

    #nametables
    ntables = None

    #sprites
    sprites = None

    #palette
    palette = Palette()

    #position stuff
    sl = -1
    cyc = 0
    current_x = 0
    current_xt = 0
    current_fx = 0
    current_y = 0
    current_yt = 0
    current_fy = 0
    stored_x = 0
    stored_xt = 0
    stored_fx = 0
    stored_y = 0
    stored_yt = 0
    stored_fy = 0
    nt_addr = 0x2000

    #ppu control register
    do_nmi = False
    sprite_size = False
    bg_pat_addr = 0x0
    spr_pat_addr = 0x0
    addr_inc = 0x1
    base_name_table = 0x2000

    #ppu mask register
    colors = 0x0
    show_bg = False
    show_spr = False
    clip_bg = False
    clip_spr = False
    grayscale = False

    #ppu status register
    pstat = 0b10100000


    def __init__(self, mach):
        self.ppu_mem = array('B')
        self.ppu_mem.fromlist([0xff] * (0x4000))
        self.obj_mem = array('B')
        self.obj_mem.fromlist([0xff] * (0x100))
        self.process_patterns()

        self.ntables = [None,None,None,None]

        self.mirror_table = array('B')
        self.mirror_table.fromlist(range(0x4000))
        this.set_mirror(0x3000, 0x2000, 0xf00)
        this.set_mirror(0x4000, 0x0000, 0x4000)
        if self.rom.flags6 & 1:
            #vertical mirror
            self.ntables[0] = NameTable()
            self.ntables[1] = NameTable()
            self.ntables[2] = self.ntables[0]
            self.ntables[3] = self.ntables[1]
            self.set_mirror(0x2800, 0x2000, 0x400)
            self.set_mirror(0x2c00, 0x2400, 0x400)
        else:
            #horiz mirror
            self.ntables[0] = NameTable()
            self.ntables[1] = self.ntables[0]
            self.ntables[2] = NameTable()
            self.ntables[3] = self.ntables[2]
            self.set_mirror(0x2400, 0x2000, 0x400)
            self.set_mirror(0x2c00, 0x2800, 0x400)

            
    def set_mirror(self, frm, to, size):
        for i in range(size):
            self.mirror_table[frm+i] = to+i

    def write_mem(self, addr, val):
        if addr < 0x2000:
            #pattern table
            assert(self.nes.rom.chr_ram)
            self.nes.rom.chr_rom[addr] = val
            self.patterns.update(addr)
        elif addr < 0x23c0:
            self.ppu_mem[addr] = val
            ntables[0].write_byte(addr&0x3ff, val)
        elif addr < 0x2400:
            self.ppu_mem[addr] = val
            ntables[0].write_attrib(addr&0x3f, val)
        elif addr < 0x27c0:
            self.ppu_mem[addr] = val
            ntables[1].write_byte(addr&0x3ff, val)
        elif addr < 0x2800:
            self.ppu_mem[addr] = val
            ntables[1].write_attrib(addr&0x3f, val)
        elif addr < 0x2bc0:
            self.ppu_mem[addr] = val
            ntables[2].write_byte(addr&0x3ff, val)
        elif addr < 0x2c00:
            self.ppu_mem[addr] = val
            ntables[2].write_attrib(addr&0x3f, val)
        elif addr < 0x2fc0:
            self.ppu_mem[addr] = val
            ntables[3].write_byte(addr&0x3ff, val)
        elif addr < 0x3000:
            self.ppu_mem[addr] = val
            ntables[3].write_attrib(addr&0x3f, val)
        elif addr >= 0x3f00 && address < 0x4000:
            self.ppu_mem[addr] = val
            self.palette.update()
        else:
            self.ppu_mem[addr] = val

    def read_mem(self, addr):
        return self.ppu_mem[addr]

    def read_mem_mirrored(self, addr):
        return self.ppu_mem[self.mirror_table[addr]]

    def write_register(self, i):
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
            self.update_sprites()
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
 

    def read_register(self, i):
        #ppu
        if i == 2:
            ret = self.pstat
            self.pstat &= ~(1 << 7)
            self.platch = False
            return ret
        elif i == 4:
            ret = self.obj_mem[self.obj_addr]
            return ret
        elif i == 7:
            if self.paddr < 0x3f00:
                res = self.ppu_mem_buf
                self.ppu_mem_buf = self.ppu_get_mem(self.vaddr)
                self.paddr += 32 if self.pctrl & (1 << 2) else 1
                self.paddr &= 0x3fff
                return res
            else:
                #needs to do some crap, also still get mirrored mem
                res = self.ppu_get_mem(self.vaddr)
                self.paddr += 32 if self.pctrl & (1 << 2) else 1
                self.paddr &= 0x3fff
                return res
        else:
            return 0

    def render_scanline(self):
        current_fx = stored_fx
        current_xt = stored_xt
        for i in range(

    def catchup(self):
        pass


