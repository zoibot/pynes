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
        self.tile = array('B')
        self.tile.fromlist([0xff]*(self.width*self.height))
        self.attrib = array('B')
        self.attrib.fromlist([0x0]*(self.width*self.height))

    def get_byte(self, x, y):
        return self.tile[y*self.width+x]

    def write_byte(self, offset, val):
        self.tile[offset] = val

    def get_attrib(self, x, y):
        return self.attrib[y*self.width+x]

    def write_attrib(self, ix, val):
        basex = (ix & 7) << 2
        basey = (ix >> 3) << 2
        for yy in range(2):
            for xx in range(2):
                att = (val >> ((((yy<<1)+xx))<<1)) & 3
                for y in range(2):
                    for x in range(2):
                        tilex, tiley = basex+xx*2+x, basey+yy*2+y
                        self.attrib[tiley*self.width+tilex] = att << 2

class PatternTables(object):
    patterns = None
    def __init__(self, nes):
        self.patterns = {}
        self.nes = nes

    def update_all(self):
        for i in xrange(0,0x2000,16):
            self.update(i)

    def update(self, addr):
        for y in xrange(8):
            lo = self.nes.rom.chr_rom[addr + y]
            hi = self.nes.rom.chr_rom[addr + y + 8]
            self.patterns[addr,y] = [((lo >> (7-x)) & 1) | (((hi >> (7-x)) & 1) << 1) for x in xrange(8)] 

    def get(self, addr, y):
        return self.patterns[addr,y]
    
class Palette(object):
    #TODO grayscale
    bg_palette = None
    spr_palette = None
    ppu = None
    def __init__(self, ppu):
        self.bg_palette = array('I')
        self.bg_palette.fromlist([0]*16)
        self.spr_palette = array('I')
        self.spr_palette.fromlist([0]*16)
        self.ppu = ppu
        self.update()
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

    #pattern tables
    patterns = None

    #sprites
    sprites = None

    #palette
    palette = None

    #position stuff
    sl = -1
    last_sl = 0
    cyc = 0
    current_xnt = 0
    current_xt = 0
    current_fx = 0
    current_ynt = 0
    current_yt = 0
    current_fy = 0
    stored_xnt = 0
    stored_xt = 0
    stored_fx = 0
    stored_ynt = 0
    stored_yt = 0
    stored_fy = 0

    #ppu control register
    do_nmi = False
    sprite_size = False
    bg_pat_addr = 0x0
    spr_pat_addr = 0x0
    addr_inc = 0x1
    base_name_table = 0

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
        self.nes = mach

        self.ppu_mem = array('B')
        self.ppu_mem.fromlist([0xff] * (0x4000))
        self.obj_mem = array('B')
        self.obj_mem.fromlist([0xff] * (0x100))

        self.patterns = PatternTables(mach)
        self.patterns.update_all()

        self.palette = Palette(self)

        self.ntables = [None,None,None,None]

        self.mirror_table = array('H')
        self.mirror_table.fromlist(range(0x4000))
        self.set_mirror(0x3000, 0x2000, 0xf00)
        #self.set_mirror(0x4000, 0x0000, 0x4000)
        if self.nes.rom.flags6 & 1:
            #vertical mirror
            self.ntables[0] = NameTable(0)
            self.ntables[1] = NameTable(1)
            self.ntables[2] = self.ntables[0]
            self.ntables[3] = self.ntables[1]
            self.set_mirror(0x2800, 0x2000, 0x400)
            self.set_mirror(0x2c00, 0x2400, 0x400)
        else:
            #horiz mirror
            self.ntables[0] = NameTable(0)
            self.ntables[1] = self.ntables[0]
            self.ntables[2] = NameTable(2)
            self.ntables[3] = self.ntables[2]
            self.set_mirror(0x2400, 0x2000, 0x400)
            self.set_mirror(0x2c00, 0x2800, 0x400)

            
    def set_mirror(self, frm, to, size):
        for i in range(size):
            self.mirror_table[frm+i] = to+i

    def write_mem(self, addr, val):
        self.catchup()
        if addr < 0x2000:
            #pattern table
            if not (self.nes.rom.chr_ram):
                return
            self.nes.rom.chr_rom[addr] = val
            self.patterns.update(addr & 0x1ff0)
        elif addr < 0x23c0:
            self.ppu_mem[self.mirror_table[addr]] = val
            self.ntables[0].write_byte(addr&0x3ff, val)
        elif addr < 0x2400:
            self.ppu_mem[self.mirror_table[addr]] = val
            self.ntables[0].write_attrib(addr&0x3f, val)
        elif addr < 0x27c0:
            self.ppu_mem[self.mirror_table[addr]] = val
            self.ntables[1].write_byte(addr&0x3ff, val)
        elif addr < 0x2800:
            self.ppu_mem[self.mirror_table[addr]] = val
            self.ntables[1].write_attrib(addr&0x3f, val)
        elif addr < 0x2bc0:
            self.ppu_mem[self.mirror_table[addr]] = val
            self.ntables[2].write_byte(addr&0x3ff, val)
        elif addr < 0x2c00:
            self.ppu_mem[self.mirror_table[addr]] = val
            self.ntables[2].write_attrib(addr&0x3f, val)
        elif addr < 0x2fc0:
            self.ppu_mem[self.mirror_table[addr]] = val
            self.ntables[3].write_byte(addr&0x3ff, val)
        elif addr < 0x3000:
            self.ppu_mem[self.mirror_table[addr]] = val
            self.ntables[3].write_attrib(addr&0x3f, val)
        elif addr >= 0x3f00 and addr < 0x4000:
            self.ppu_mem[self.mirror_table[addr]] = val
            self.palette.update()
        else:
            self.ppu_mem[self.mirror_table[addr]] = val

    def read_mem(self, addr):
        return self.ppu_mem[addr]

    def read_mem_mirrored(self, addr):
        return self.ppu_mem[self.mirror_table[addr]]

    def currents_to_address(self):
        t1 = (self.current_fy)<<4
        t1 |= (self.current_ynt)<<3
        t1 |= (self.current_xnt)<<2
        t1 |= (self.current_yt>>3)&3
        t2 = (self.current_yt & 7)<<5
        t2 |= self.current_xt & 31

        self.vaddr = ((t1<<8) | t2)&0x3fff

    def address_to_currents(self):
        hi = self.vaddr >> 8
        self.current_fy = (hi>>4)&3
        self.current_ynt = (hi>>3)&1
        self.current_xnt = (hi>>2)&1
        self.current_yt = (self.current_yt&7) | ((hi&3)<<3)
        lo = self.vaddr & 0xff
        self.current_yt = (self.current_yt&24) | ((lo>>5)&7)
        self.current_xt = lo & 31

    #TODO rewrite these
    def write_register(self, i, val):
        self.catchup()
        if i == 0:
            self.pctrl = val
            self.stored_xnt = val & 1
            self.stored_ynt = (val & 2) >> 1
            self.addr_inc = 32 if (val & 4) else 1
            self.spr_pat_addr = 0x1000 if val & 8 else 0
            self.bg_pat_addr = 0x1000 if val & 16 else 0
            self.sprite_size = val & 32
            self.do_nmi = val & 128
        elif i == 1:
            self.pmask = val
            self.grayscale = val & 1
            self.clip_bg = val & 2
            self.clip_spr = val & 4
            self.show_bg = val & 8
            self.show_spr = val & 16
            self.color = (val & 112) >> 4
        elif i == 3:
            self.oamaddr = val
        elif i == 4:
            self.obj_mem[self.oamaddr] = val
            #self.update_sprites()
            self.oamaddr += 1
            self.oamaddr &= 0xff
        elif i == 5:
            if self.platch:
                self.stored_fy = val & 7
                self.stored_yt = (val >> 3)
                self.platch = False
            else:
                self.stored_xt = (val >> 3)
                self.stored_fx = val & 0x7
                self.current_fx = val & 0x7
                self.platch = True
        elif i == 6:
            if self.platch:
                self.stored_yt = (self.stored_yt & 24) | ((val>>5)&7)
                self.stored_xt = val & 31
                self.current_fy = self.stored_fy
                self.current_ynt = self.stored_ynt
                self.current_xnt = self.stored_xnt
                self.current_yt = self.stored_yt
                self.current_xt = self.stored_xt
                self.currents_to_address()
                self.platch = False
            else:
                self.stored_fy = (val >> 4) & 3
                self.stored_ynt = (val >> 3) & 1
                self.stored_xnt = (val >> 2) & 1
                self.stored_yt = (self.stored_yt & 7) | ((val &3)<<3)
                self.platch = True
        elif i == 7:
            self.currents_to_address()
            self.write_mem(self.vaddr, val)
            self.vaddr += self.addr_inc
            self.vaddr &= 0x3fff
            self.address_to_currents()
 

    def read_register(self, i):
        self.catchup()
        if i == 2:
            ret = self.pstat
            self.pstat &= ~(1 << 7)
            self.platch = False
            return ret
        elif i == 4:
            ret = self.obj_mem[self.obj_addr]
            return ret
        elif i == 7:
            self.currents_to_address()
            if self.vaddr < 0x3f00:
                res = self.ppu_mem_buf
                self.ppu_mem_buf = self.read_mem_mirrored(self.vaddr)
            else:
                #needs to do some crap, also still get mirrored mem
                res = self.read_mem_mirrored(self.vaddr)
            self.vaddr += self.addr_inc
            self.vaddr &= 0x3fff
            self.address_to_currents()
            return res
        else:
            return 0

    def render_scanline(self):
        #update horizontal scan
        self.last_sl += 1
        if not self.show_bg:
            return
        self.current_fx = self.stored_fx
        self.current_xt = self.stored_xt
        xt = self.current_xt
        cur_nt = self.ntables[self.current_ynt + self.current_ynt + self.current_xnt]
        g_b = cur_nt.get_byte
        g_a = cur_nt.get_attrib
        pat_get = self.patterns.get
        bg_pat_addr = self.bg_pat_addr
        x = self.current_fx
        for tile in xrange(32):
            t = pat_get(bg_pat_addr + 0x10*g_b(xt, self.current_yt), self.current_fy)
            att = g_a(xt, self.current_yt)
            for i in xrange(8):
                col = t[i]
                if col:
                    col += att
                self.nes.pixels[x+i, self.last_sl] = self.palette.bg_palette[col]
            if xt == 32:
                xt = 0
                self.current_xnt = (self.current_xnt + 1)%2
                cur_nt = self.ntables[self.current_ynt + self.current_ynt + self.current_xnt]
            else:
                xt += 1
            x += 8
        self.current_fy += 1
        if self.current_fy == 8:
            self.current_fy  = 0
            self.current_yt += 1
            if self.current_yt == 30:
                self.current_yt = 0
                self.current_ynt = (self.current_ynt + 1) % 2
            elif self.current_yt == 32:
                self.current_yt = 0

    def end_scanline(self):
        if self.sl == 19:
            pass
            #dummy cycle???
            #self.cyc = 1
        elif self.sl == 20:
            self.pstat &= ~(3 << 6)
            if self.show_bg or self.show_spr:
                self.current_fy = self.stored_fy
                self.current_ynt = self.stored_ynt
                self.current_xnt = self.stored_xnt
                self.current_yt = self.stored_yt
                self.current_xt = self.stored_xt
        elif self.sl == 261:
            self.catchup()
            self.pstat |= 1 << 7
            if self.do_nmi:
                self.nes.nmi(0xfffa)
            self.draw_frame()
        elif self.sl >= 21 and self.sl <= 260:
            pass
        self.sl += 1

    def draw_frame(self):
        self.sl = -1
        self.last_sl = 0
        self.nes.surface.unlock()
        pygame.display.flip()
        self.nes.surface.fill(0x0)
        self.nes.surface.lock()
        pygame.event.pump()
        self.nes.clock.tick()
        print 'frame ', self.nes.frame_count
        print self.nes.clock.get_fps()
        self.nes.frame_count += 1

    def catchup(self):
        while self.last_sl + 1 < self.sl-21:
            self.render_scanline()

    def run(self, cycles):
        #should do sprite 0 hit???
        self.cyc += cycles
        while self.cyc > 341:
            self.cyc -= 341
            self.end_scanline()


