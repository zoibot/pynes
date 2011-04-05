#include <cstring>

#include "ppu.h"
#include "machine.h"

PPU::PPU(Machine *mach, sf::RenderWindow* wind) {
    this->mach = mach;
    this->wind = wind;
    screen.Create(256, 240);
    screen.SetSmooth(false);
	debugi.Create(512, 480);
	debugi.SetSmooth(false);
    vaddr = 0;
    obj_addr = 0;
    mem = new byte[0x4000];
    obj_mem = new byte[0x100];
    debug_flag = false;
    cycle_count = 0;
    sl = 0;
    cyc = 0;
	pmask = 0;
	pctrl = 0;
    pstat = 0;
    last_vblank_end = last_vblank_start = 0;
    memset(mem, 0xff, 0x4000);
    memset(obj_mem, 0xff, 0x100);
    mirror_table = new word[0x4000];
    for(int i = 0; i < 0x4000; i++)
        mirror_table[i] = i;
    set_mirror(0x3000, 0x2000, 0xf00);
	if(mach->rom->flags6 & 8) {
		cout << "4 screen!!!!" << endl;
	}
	current_mirroring = FOUR_SCREEN;
	set_mirroring(mach->rom->mirror);
	//set_mirroring(SINGLE_LOWER);
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
            mem_buf = get_mem(vaddr-0x1000);
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
        return mach->rom->chr_rom[(addr&0x1000)>>12][addr&0xfff];
    } else if(addr < 0x3000) {
        return mem[mirror_table[addr]];
    } else if(addr < 0x3f00) {
        return get_mem(addr - 0x1000);
    } else {
        if((addr & 0xf) == 0) addr = 0;
        return mem[0x3f00 + (addr&0x1f)];
    }
}

void PPU::set_mem(word addr, byte val) {
    if(addr < 0x2000) {
        mach->rom->chr_rom[(addr&0x1000)>>12][addr&0xfff] = val;
    } else if(addr < 0x3f00) {
        mem[mirror_table[addr]] = val;
    } else {
        if((addr & 0xf) == 0) addr = 0;
        mem[0x3f00 + (addr&0x1f)] = val;
    }
}

void PPU::new_scanline() {
    int fineY = (vaddr & 0x7000) >> 12;
    if(fineY == 7) {
        if((vaddr & 0x3ff) >= 0x3c0) {
			vaddr &= ~0x3ff;
        } else {
			vaddr += 0x20;
			if((vaddr & 0x3ff) >= 0x3c0) {
				vaddr &= ~0x3ff;
				vaddr ^= 0x800;
			}
		}
    }
    vaddr &= ~0x741f;
    vaddr |= next_taddr & 0x1f;
    vaddr |= next_taddr & (0x400);
    vaddr |= ((fineY+1)&7) << 12;
    fine_x = xoff;
    next_taddr = -1;
    //sprites
    cur_sprs.clear();
    //cout << (int)(((Sprite*)obj_mem) + 3)->y << endl;
    for(int i = 0; i < 64; i++) {
        Sprite *s = ((Sprite*)obj_mem)+i;
		if(s->y <= (sl-1) && ((sl-1) < s->y+8 || ((pctrl & (1<<5)) && (sl-1) < s->y+16))) {
			if(i == 0 && s->y >= 238) {
				debug_flag = true;
			}
            cur_sprs.push_back(s);
        }
    }
}

void PPU::do_vblank(bool rendering_enabled) {
    int cycles = mach->cycle_count * 3 - cycle_count;
	if(last_vblank_end < last_vblank_start) {
		last_vblank_end = mach->cycle_count;
		cout << (last_vblank_start - last_vblank_end) << endl;
	}
	pstat &= ~(1 << 7);
    if(341 - cyc > cycles) {
        cyc += cycles;
        cycle_count += cycles;
    } else {
        cycle_count += 341 - cyc;
        cyc = 0;
        sl += 1;
        if(rendering_enabled) {
            vaddr = taddr;
            fine_x = xoff;
        }
    }
}

void PPU::render_pixels(byte x, byte y, byte num) {
    bool bg_enabled = pmask & (1 << 3);
    bool sprite_enabled = pmask & (1 << 4);
    int fineY = (vaddr >> 12) & 7;
    int xoff = cyc;
    word base_pt_addr;
    if(pctrl & (1<<4)) {
        base_pt_addr = 0x1000;
    } else {
        base_pt_addr = 0x0;
    }
    word base_spr_addr;
    if(pctrl & 8) {
        base_spr_addr = 0x1000;
    } else {
        base_spr_addr = 0x0;
    }
    while(num) {
        word nt_addr = 0x2000 | (vaddr & 0xfff);
        word at_base = (nt_addr & (~0x3ff)) + 0x3c0;
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
        if((hi|lo) && bg_enabled && !(xoff < 8 && !(pmask & 2)))
            coli |= at_val | hi | lo;
		if(debug_flag) {
			cout << "on the outside" << endl;
			cout << sprite_enabled << endl;
			//cin.get();
		}
        if(sprite_enabled && !(xoff < 8 && !(pmask & 4))) {
            Sprite *cur = NULL;
            for(list<Sprite*>::iterator i = cur_sprs.begin(); i != cur_sprs.end(); i++) {
                if(((*i)->x <= xoff) && (xoff < ((*i)->x+8))) {
                    cur = (*i);
                    byte pal = (1<<4) | ((cur->attrs & 3) << 2);
                    byte xsoff = xoff-cur->x;
                    if(cur->attrs & (1<<6))
                        xsoff = 7-xsoff;
                    byte ysoff = y-cur->y-1;
					byte tile;
					if(pctrl & (1<<5)) {
						if(cur->attrs & (1<<7))
							ysoff = 15-ysoff;
						tile = cur->tile;
						base_spr_addr = (tile & 1) << 12;
						tile &= ~1;
						if(ysoff > 7) {
							ysoff -= 8;
							tile |= 1;
						}
					} else {
						tile = cur->tile;
						if(cur->attrs & (1<<7))
							ysoff = 7-ysoff;
					}
                    word pat = (tile * 0x10) | base_spr_addr;
                    byte shi = get_mem(pat+8+ysoff);
                    byte slo = get_mem(pat+ysoff);
                    shi >>= (7-xsoff);
                    shi &= 1;
                    shi <<= 1;
                    slo >>= (7-xsoff);
                    slo &= 1;
					/*if(y >= 238) {
						cout << "spr " << endl;
						cout << "y: " << cur->y << endl;
						cout << "x: " << cur->x << endl;
					}*/
                    if((cur == (Sprite*)obj_mem) && (shi|slo) && (hi|lo) && bg_enabled && !(xoff < 8 && !(pmask & 2)) && xoff < 255) {
                        pstat |= 1<<6; // spr hit 0
                       /* cout << " sprite 0 hit " << endl;
                        cout << int(xoff) << endl;
                        cout << int(y) << endl;
                        cout << HEX2(cur->attrs) << endl;
                        cout << HEX2(cur->x) << endl;
                        cout << HEX2(cur->y) << endl;
                        cout << HEX2(cur->tile) << endl;*/
                    }
                    if((!(hi|lo) && (shi|slo)) || !(cur->attrs & (1<<5))) {
                        if(shi|slo) {
                            coli = 0x3f00 | pal | shi | slo;
                            break;
                        }
                    }
                }
            }
        }
		debug_flag = false;
        int color = colors[get_mem(coli)];
        screen.SetPixel(xoff, y, sf::Color((color & 0xff0000)>>16, (color & 0x00ff00) >> 8, color & 0x0000ff));
        fine_x++;
        fine_x &= 7;
        xoff++;
        if(!fine_x) {
            if((vaddr & 0x1f) == 0x1f) {
                vaddr ^= 0x400;
                vaddr -= 0x1f;
            } else {
                vaddr++;
            }
        }
        num--;
    }
}

void PPU::draw_frame() {
    sl = -2;
	sf::Sprite x(screen);
    wind->Draw(x);
    //process events
    sf::Event event;
	bool paused = false;
	do {
		while (wind->GetEvent(event)) {
			if (event.Type == sf::Event::Closed) {
                mach->save();
				wind->Close();
				exit(0);
			} else if (event.Type == sf::Event::KeyReleased) {
				if(event.Key.Code == sf::Key::T) {
					screen.SaveToFile("sshot.jpg");
				} else if(event.Key.Code == sf::Key::N) {
					dump_nts();
				} else if(event.Key.Code == sf::Key::P) {
					paused = !paused;
				} else if(event.Key.Code == sf::Key::Y) {
					for(int i = 0; i < 64; i++) {
						Sprite *s = ((Sprite*)obj_mem)+i;
						if(s->y < 16) {
							cout << (int)s->y << endl;
						}
					}
				} else if(event.Key.Code == sf::Key::D) {
					mach->debug = false;
				} else if(event.Key.Code == sf::Key::Q) {
					//ZOOOM
					wind->SetSize(1024, 960);
				}
			}
		}
	} while (paused);
    wind->Display();
}

void PPU::run() {
    bool bg_enabled = pmask & (1 << 3);
    bool sprite_enabled = pmask & (1 << 4);
    bool rendering_enabled = bg_enabled || sprite_enabled;
    int cycles = mach->cycle_count * 3 - cycle_count;
    while(cycle_count < mach->cycle_count * 3) {
        if(sl == -2) {
            do_vblank(rendering_enabled);
		} else if(sl == -1) {
			cycle_count += 341;
			sl += 1;
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
            } else if(cyc >= 257) {
                next_taddr = taddr;
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
                pstat |= (1 << 7);
				last_vblank_start = mach->cycle_count;
                pstat &= ~(1 << 6);
                if(pctrl & (1 << 7)) {
                    mach->nmi(0xfffa);
                }
            }
        } else {
            cycle_count += 341 * 20;
            draw_frame();
        }
    }           
}

void PPU::set_mirroring(NTMirroring mirror) {
	if(mirror == current_mirroring) return;
	switch(mirror) {
	case VERTICAL:
		set_mirror(0x2000, 0x2000, 0x400);
		set_mirror(0x2400, 0x2400, 0x400);
		set_mirror(0x2800, 0x2000, 0x400);
        set_mirror(0x2c00, 0x2400, 0x400);
		break;
	case HORIZONTAL:
		set_mirror(0x2000, 0x2000, 0x400);
		set_mirror(0x2400, 0x2000, 0x400);
		set_mirror(0x2800, 0x2400, 0x400);
        set_mirror(0x2c00, 0x2400, 0x400);
		break;
	case SINGLE_LOWER:
		set_mirror(0x2000, 0x2000, 0x400);
		set_mirror(0x2400, 0x2000, 0x400);
		set_mirror(0x2800, 0x2000, 0x400);
        set_mirror(0x2c00, 0x2000, 0x400);
		break;
	case SINGLE_UPPER:
		set_mirror(0x2000, 0x2400, 0x400);
		set_mirror(0x2400, 0x2400, 0x400);
		set_mirror(0x2800, 0x2400, 0x400);
        set_mirror(0x2c00, 0x2400, 0x400);
		break;
	case SINGLE_THIRD:
		set_mirror(0x2000, 0x2800, 0x400);
		set_mirror(0x2400, 0x2800, 0x400);
		set_mirror(0x2800, 0x2800, 0x400);
        set_mirror(0x2c00, 0x2800, 0x400);
		break;
	case SINGLE_FOURTH:
		set_mirror(0x2000, 0x2c00, 0x400);
		set_mirror(0x2400, 0x2c00, 0x400);
		set_mirror(0x2800, 0x2c00, 0x400);
        set_mirror(0x2c00, 0x2c00, 0x400);
		break;
	default:
		break;
	}
}


void PPU::dump_nts() {
	debug.Create(sf::VideoMode(512, 480), "debug");
	word base_pt_addr;
	if(pctrl & (1<<4)) {
        base_pt_addr = 0x1000;
    } else {
        base_pt_addr = 0x0;
    }
	int x = 0;
	int y = 0;
	for(int nt = 0x2000; nt < 0x3000; nt+=0x400) {
		word at_base = nt + 0x3c0;
		for(int ntaddr = nt; ntaddr < nt+0x3c0; ntaddr++) {
			byte nt_val = get_mem(ntaddr);
			word pt_addr = (nt_val << 4) + base_pt_addr;
			byte row = (ntaddr >> 6) & 1;
			byte col = (ntaddr & 2) >> 1;
			byte at_val = get_mem(at_base + ((ntaddr & 0x1f)>>2) + ((ntaddr & 0x3e0) >> 7)*8);
			at_val >>= 4 * row + 2 * col;
			at_val &= 3;
			at_val <<= 2;
			for(int fy = 0; fy < 8; fy++) {
				for(int fx = 0; fx < 8; fx++) {
					byte hi = get_mem(pt_addr+8+fy);
					byte lo = get_mem(pt_addr+fy);
					hi >>= (7-fx);
					hi &= 1;
					hi <<= 1;
					lo >>= (7-fx);
					lo &= 1;
					word coli = 0x3f00;
					if(hi|lo)
						coli |= at_val | hi | lo;
					int color = colors[get_mem(coli)];
					debugi.SetPixel(x+fx, y+fy, sf::Color((color & 0xff0000)>>16, (color & 0x00ff00) >> 8, color & 0x0000ff));
				}
			}
			x += 8;
			if(x % 256 == 0) {
				x -= 256;
				y += 8;
			}
		}
		x += 256;
		y -= 240;
		if(x == 512) {
			x = 0;
			y = 240;
		}
	}
	debug.Draw(sf::Sprite(debugi));
	debug.Display();
}
