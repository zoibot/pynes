#include "machine.h"

void Machine::set_flag(char flag, bool val) {
    if(val) {
        p |= flag;
    } else {
        p &= ~flag;
    }
}
bool Machine::get_flag(char flag) {
    return flag & p;
}
void Machine::set_nz(char val) {
    set_flag(Z, val == 0)
    set_flag(N, val & 0x80)
}

char Machine::next_byte() {
    return self.get_code_mem(self.pc++);
}
char Machine::next_word() {
    return self.next_byte() | (self.next_byte() << 8)
}

char Machine::get_mem(short addr) {
    if(addr < 0x2000) {
        return mem[addr & 0x7ff];
    } else if(addr < 0x4000) {
        return ppu->read_register((addr - 0x2000)&7)
    } else if(addr < 0x4018) {
        if(addr == 0x4016) {
            if(read_input_state < 8) {
                return keys[read_input_state++];
            } else {
                return 1;
            }
        }
        return 0; //alu
    } else if(addr < 0x8000) {
        return rom->prg_ram[addr-0x6000];
    } else if(addr < 0xC000 || rom->prg_size > 1) {
        return rom->prg_rom[addr-0x8000];
    } else {
        return rom->prg_rom[addr-0xC000];
    }
}

char Machine::get_code_mem(short addr) {
    if(addr > 0x8000) {
        return rom.prg_rom[addr & 0x3fff];
    } else {
        return get_mem(addr);
    }
}

void Machine::set_mem(addr, val) {
    if(addr < 0x2000) {
        mem[addr & 0x7ff] = val;
    } else if(addr < 0x4000) {
        ppu->write_register((addr - 0x2000)&7, val);
    } else if(addr < 0x4018) {
        if(addr = 0x4016) {
            if(val & 1) {
                for(int i = 0; i < 8; i++) {
                    keys[i] = sf::Input.IsKeyDown(keymap[i]);
                }
            }
            read_input_state = 0;
        } else if (addr == 0x4014) {
            short start = val << 8;
            short end = start + 0x100;
            //TODO ppu set obj mem
        }
        //ALU
    } else if(addr < 0x8000) {
        rom.prg_ram[addr-0x6000] = val;
    }
}

void Machine::push2(val) {
    s -= 2;
    short ss = s | 0x0100;
    set_mem(ss+1, val & 0xff);
    set_mem(ss+2, val >> 8);
}
short Machine::pop2() {
    s += 2;
    ss = s | 0x100;
    return get_mem(ss-1) + (get_mem(ss) << 8);
}
void Machine::push(val) {
    self.set_mem(s-- | 0x100, val);
}
char Machine::pop() {
    return get_mem(++s | 0x100);
}

string Machine::dump_regs() {
    return "";
}

Machine::Machine(Rom *rom) {
    this->rom = rom;
    //Display
    wind.Create(sf::VideoMode(800, 600), "SFML window");
    //print surface bits
    ppu = new PPU(this);
    //get pixel array from ppu
    //clock???
    mem = new char[0x800];
    for(int i = 0; i < 0x800; i++) {
        mem[i] = 0xff;
    }
}

void Machine::execute_inst() {
    switch(inst.opcode) {
    }
}

void Machine::run() {
    while(1) {
        inst = Instruction.next_instruction();
        execute_inst();
        ppu->run();
    }
}

