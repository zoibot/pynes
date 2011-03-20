#include <cstring>

#include "ppu.h"
#include "machine.h"

PPU::PPU(Machine *mach, sf::RenderWindow* wind) {
    this->mach = mach;
    this->wind = wind;
    screen.Create(256, 240);
    screen.SetSmooth(false);
    vaddr = 0;
    obj_addr = 0;
    mem = new byte[0x4000];
    obj_mem = new byte[0x100];
    cycle_count = 0;
    sl = 0;
    cyc = 0;
    memset(mem, 0xff, 0x4000);
    mirror_table = new word[0x4000];
    for(int i = 0; i < 0x4000; i++)
        mirror_table[i] = i;
    set_mirror(0x3000, 0x2000, 0xf00);
    if(mach->rom->flags6 & 1) {
        set_mirror(0x2800, 0x2000, 0x400);
        set_mirror(0x2c00, 0x2400, 0x400);
    } else {
        set_mirror(0x2400, 0x2000, 0x400);
        set_mirror(0x2c00, 0x2800, 0x400);
    }
}

byte PPU::read_register(byte num) {
    byte ret;
    switch(num) {
    case 2:
        ret = pstat;
        pstat &= ~(1 << 7);
        latch = false;
        return ret;
    case 4:
        ret = obj_mem[obj_addr];
        return ret;
    case 7:
        if(vaddr < 0x3f00) {
            ret = mem_buf;
            mem_buf = get_mem(vaddr);
        } else {
            ret = get_mem(vaddr);
        }
        if(pctrl & (1 << 2)) {
            vaddr += 32;
        } else {
            vaddr += 1;
        }
        vaddr &= 0x3fff;
        return ret;
    }
    return 0;
}

void PPU::write_register(byte num, byte val) {
    switch(num) {
    case 0:
        pctrl = val;
        taddr &= (~(0x3 << 10));
        taddr |= (val & 0x3) << 10;
        break;
    case 1:
        pmask = val;
        break;
    case 3:
        obj_addr = val;
        break;
    case 4:
        obj_mem[obj_addr] = val;
        obj_addr += 1;
        obj_addr &= 0xff;
        break;
    case 5:
        if(latch) {
            taddr &= (~0x73e0);
            taddr |= (val >> 3) << 5;
            taddr |= (val & 0x7) << 12;
        } else {
            taddr &= ~0x1f;
            taddr |= val >> 3;
            xoff = val & 0x7;
            fine_x = val & 0x7;
        }
        latch = !latch;
        break;
    case 6:
        if(latch) {
            taddr &= ~0xff;
            taddr |= val;
            vaddr = taddr;
        } else {
            taddr &= 0xff;
            taddr |= (val & 0x3f) << 8;
        }
        latch = !latch;
        break;
    case 7:
        set_mem(vaddr, val);
        if(pctrl & (1 << 2)) {
            vaddr += 32;
        } else {
            vaddr += 1;
        }
        vaddr &= 0x3fff;
        break;
    }
}

void PPU::set_mirror(word from, word to, word size) {
    for(word i = 0; i < size; i++) {
        mirror_table[from+i] = to+i;
    }
}

byte PPU::get_mem_mirrored(word addr) {
    return get_mem(mirror_table[addr]);
}

byte PPU::get_mem(word addr) {
    if(addr < 0x2000) {
        return mach->rom->chr_rom[addr];
    } else if(addr < 0x3000) {
        return mem[mirror_table[addr]];
    } else if(addr < 0x3f00) {
        return get_mem(addr - 0x1000);
    } else {
        return mem[mirror_table[addr]];
    }
}

void PPU::set_mem(word addr, byte val) {
    if(addr < 0x2000) {
        //should set rom???
    } else {
        mem[mirror_table[addr]] = val;
    }
}

void PPU::new_scanline() {
    int fineY = (vaddr & 0x7000) >> 12;
    if(fineY == 7) {
        if((vaddr & 0x3ff) >= 0x3c0) {
            vaddr |= 0x800;
        }
        vaddr += 0x20;
    }
    vaddr &= ~0x741f;
    vaddr |= taddr & 0x1f;
    vaddr |= taddr & (0x400);
    vaddr |= ((fineY+1)&7) << 12;
    fine_x = xoff;
    //sprites
    cur_sprs.clear();
    for(int i = 0; i < 64; i++) {
        Sprite *s = ((Sprite*)obj_mem)+i;
        if(s->y <= (sl-1) && (sl-1) < s->y+8) {
            cur_sprs.push_back(s);
        }
    }
}

void PPU::do_vblank(bool rendering_enabled) {
    int cycles = cycle_count * 3 - cycle_count;
    if(341 - cyc > cycles) {
        cyc += cycles;
        cycle_count += cycles;
    } else {
        cycle_count += 341 - cyc;
        cyc = 0;
        sl += 1;
        pstat &= ~(3 << 6);
        if(rendering_enabled) {
            vaddr = taddr;
            fine_x = xoff;
        }
    }
}

void PPU::render_pixels(byte x, byte y, byte num) {
    int fineY = (vaddr >> 12) & 7;
    int xoff = cyc;
    word base_pt_addr;
    if(pctrl & (1<<4)) {
        base_pt_addr = 0x1000;
    } else {
        base_pt_addr = 0x0;
    }
    word base_spr_addr = 0x1000 * ((pctrl & 8) >> 3);
    while(num) {
        word nt_addr = 0x2000 | (vaddr & 0xfff);
        word at_base = (nt_addr & (~0xfff)) + 0x3c0;
        byte nt_val = get_mem(nt_addr);
        word pt_addr = (nt_val << 4) + base_pt_addr;
        byte row = (nt_addr >> 6) & 1;
        byte col = (nt_addr & 2) >> 1;
        byte at_val = get_mem(at_base + ((nt_addr & 0x1f)>>2) + ((nt_addr & 0x3e0) >> 7)*8);
        at_val >>= 4 * row + 2 * col;
        at_val &= 3;
        at_val <<= 2;
        byte hi = get_mem(pt_addr+8+fineY);
        byte lo = get_mem(pt_addr+fineY);
        hi >>= (7-fine_x);
        hi &= 1;
        hi <<= 1;
        lo >>= (7-fine_x);
        lo &= 1;
        word coli = 0x3f00;
        if(hi|lo)
            coli |= at_val | hi | lo;
        Sprite *cur = NULL;
        for(list<Sprite*>::iterator i = cur_sprs.begin(); i != cur_sprs.end(); i++) {
            if(((*i)->x <= xoff) && (xoff < ((*i)->x+8))) {
                cur = (*i);
                //TODO mirroring
                byte pal = (1<<4) | ((cur->attrs & 3) << 2);
                byte xsoff = xoff-cur->x;
                if(cur->attrs & (1<<6))
                    xsoff = 7-xsoff;
                byte ysoff = y-cur->y-1;
                if(cur->attrs & (1<<7))
                    ysoff = 7-ysoff;
                word pat = (cur->tile * 0x10) + base_spr_addr;
                byte shi = get_mem(pat+8+ysoff);
                byte slo = get_mem(pat+ysoff);
                shi >>= (7-xsoff);
                shi &= 1;
                shi <<= 1;
                slo >>= (7-xsoff);
                slo &= 1;
                if((!(hi|lo) && (shi|slo)) || !(cur->attrs & (1<<5))) {
                    if(shi|slo) {
                        if(cur == (Sprite*)obj_mem)
                            pstat |= 1<<6;
                        coli = 0x3f00 | pal | shi | slo;
                        break;
                    }
                }
            }
            //cout << "sprite " << coli << endl;
        }
        int color = colors[get_mem(coli)];
        screen.SetPixel(xoff, y, sf::Color((color & 0xff0000)>>16, (color & 0x00ff00) >> 8, color & 0x0000ff));
        fine_x++;
        fine_x &= 7;
        xoff++;
        if(!fine_x) {
            if((vaddr & 0x1f) == 0x1f) {
                vaddr |= 0x400;
                vaddr -= 0x1f;
            } else {
                vaddr++;
            }
        }
        num--;
    }
}

void PPU::draw_frame() {
    sl = -1;
    wind->Draw(sf::Sprite(screen));
    //process events
    sf::Event event;
    while (wind->GetEvent(event)) {
        if (event.Type == sf::Event::Closed) {
            wind->Close();
            exit(0);
        }
    }
    wind->Display();
    cout << "frame! " << (1/wind->GetFrameTime()) << endl;
}

void PPU::run() {
    bool bg_enabled = pmask & (1 << 3);
    bool sprite_enabled = pmask & (1 << 4);
    bool rendering_enabled = bg_enabled || sprite_enabled;
    int cycles = mach->cycle_count * 3 - cycle_count;
    while(cycle_count < mach->cycle_count * 3) {
        if(sl < 0) {
            do_vblank(rendering_enabled);
        } else if(sl < 240) {
            int todo;
            if(341 - cyc > cycles) {
                todo = cycles;
            } else {
                todo = 341 - cyc;
            }
            int y = sl;
            if(rendering_enabled && cyc < 256) {
                render_pixels(cyc, y, min(todo, 256-cyc));
            }
            cyc += todo;
            cycle_count += todo;
            if(cyc == 341) {
                cyc = 0;
                sl += 1;
                if(rendering_enabled) {
                    new_scanline();
                }
            }
        } else if(sl == 240) {
            if(341 - cyc > cycles) {
                cyc += cycles;
                cycle_count += cycles;
            } else {
                cycle_count += 341 - cyc;
                cyc = 0;
                sl += 1;
                cout << "vblank" << endl;
                pstat |= (1 << 7);
                if(pctrl & (1 << 7)) {
                    mach->nmi(0xfffa);
                }
            }
        } else {
            cycle_count += 341 * 21;
            draw_frame();
        }
    }           
}
