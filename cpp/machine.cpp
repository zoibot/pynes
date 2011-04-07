#include <cstring>
#include <fstream>

#include "machine.h"

void Machine::set_flag(byte flag, bool val) {
    if(val) {
        p |= flag;
    } else {
        p &= ~flag;
    }
}
bool Machine::get_flag(byte flag) {
    return flag & p;
}
void Machine::set_nz(byte val) {
    set_flag(Z, val == 0);
    set_flag(N, val & 0x80);
}

byte Machine::next_byte() {
    return get_code_mem(pc++);
}
word Machine::next_word() {
    return next_byte() | (next_byte() << 8);
}

void Machine::nmi(word addr) {
    push2(pc);
    push(p);
	set_flag(I, true);
    pc = get_mem(addr) + (get_mem(addr+1)<<8);
	cycle_count += 7;
}

void Machine::request_irq() {
	if(!scheduled_irq) {
		irq_waiting = true;
		if(!get_flag(I)) {
			scheduled_irq = 1;
		}
	}
}

void Machine::irq() {
	push2(pc);
    push(p);
	set_flag(I, true);
    pc = get_mem(0xfffe) + (get_mem(0xfffe+1)<<8);
	cycle_count += 7;
}

void Machine::reset() {
    cycle_count = 0;
    s = 0xff;
    a = x = y = 0;
    p = 0x24;
    s -= 2;
    s &= 0xff;
    memset(mem, 0xff, 0x800);
    mem[0x0008] = 0xf7;
    mem[0x0009] = 0xef;
    mem[0x000a] = 0xdf;
    mem[0x000f] = 0xbf;
    pc = get_mem(0xfffc) + (get_mem(0xfffd) << 8);
}

void Machine::save() {
	if(!(rom->flags6 & 2)) return;
	cout << " saving to " << (rom->fname + ".sav") << endl;
	ofstream save((rom->fname + ".sav").c_str());
    save.write((char*)rom->prg_ram, 0x2000);
	save.close();
}

byte Machine::get_mem(word addr) {
    if(addr < 0x2000) {
        return mem[addr & 0x7ff];
    } else if(addr < 0x4000) {
		//update ppu before read
		cycle_count += inst.op.cycles + inst.extra_cycles;
		ppu->run();
		cycle_count -= inst.op.cycles + inst.extra_cycles;
        return ppu->read_register((addr - 0x2000)&7);
    } else if(addr < 0x4018) {
        switch(addr) {
        case 0x4016:
            if(read_input_state < 8) {
                return keys[read_input_state++];
            } else {
                return 1;
            }
        break;
        default:
            return apu->read_register(addr - 0x4000);
            break;
        }
    } else if(addr < 0x8000) {
        return rom->prg_ram[addr-0x6000];
    } else {
        return rom->prg_rom[(addr & 0x4000)>>14][addr&0x3fff];
    }
}

byte Machine::get_code_mem(word addr) {
    if(addr >= 0x8000) {
        return rom->prg_rom[(addr & 0x4000)>>14][addr&0x3fff];
    } else {
        return get_mem(addr);
    }
}

void Machine::set_mem(word addr, byte val) {
    if(addr < 0x2000) {
        mem[addr & 0x7ff] = val;
    } else if(addr < 0x4000) {
        ppu->write_register((addr - 0x2000)&7, val);
    } else if(addr < 0x4018) {
        switch(addr) {
        case 0x4016:
            if(val & 1) {
                for(int i = 0; i < 8; i++) {
                    keys[i] = wind.GetInput().IsKeyDown(keymap[i]);
                }
            }
            read_input_state = 0;
            break;
        case 0x4014:
            for(word v = 0; v < 0x100; v++) {
                byte addr = v + ppu->obj_addr;
                ppu->obj_mem[addr] = mem[(val << 8)+v];
            }
            //TODO cycles???
            break;
        default:
            apu->write_register(addr - 0x4000, val);
            break;
        }
    } else if(addr < 0x8000) {
        rom->prg_ram[addr-0x6000] = val;
    } else {
		rom->mapper->prg_write(addr, val);
		ppu->set_mirroring(rom->mirror);
	}
}

void Machine::push2(word val) {
    s -= 2;
    word ss = 0x0100;
    set_mem(ss | (s + 1), val & 0xff);
    set_mem(ss | (s + 2), val >> 8);
}
word Machine::pop2() {
    s += 2;
    return get_mem(((s-1) & 0xff) | 0x100) + (get_mem(s | 0x100) << 8);
}
void Machine::push(byte val) {
    set_mem(s-- | 0x100, val);
}
byte Machine::pop() {
    return get_mem(++s | 0x100);
}

string Machine::dump_regs() {
    stringstream out;
    out << hex << uppercase;
    out << "A:" << HEX2(a);
    out << " X:" << HEX2(x);
    out << " Y:" << HEX2(y);
    out << " P:" << HEX2(p);
    out << " SP:" << HEX2(s);
	out << dec;
    out << " CYC:" << ppu->cyc;
    out << " SL:" << ppu->sl;
	out << " VADDR: " << HEX4(ppu->vaddr);
	int end;
	if(ppu->last_vblank_end > ppu->last_vblank_start) {
		end = ppu->last_vblank_end;
	} else {
		end = cycle_count;
	}
	out << " FC: " << dec << (end - ppu->last_vblank_start);
    return out.str();
}

Machine::Machine(Rom *rom) {
    this->rom = rom;
    inst.mach = this;
	debug = false;
    //Display
    wind.Create(sf::VideoMode(256, 240), "asdfNES", sf::Style::Close);
    wind.SetFramerateLimit(60);// what is the right limit??
    //print surface bits
    cout << "Depth Bits: " << wind.GetSettings().DepthBits << endl;
    ppu = new PPU(this, &wind);
	apu = new APU(this);
    //clock???
    mem = new byte[0x800];
    memset(mem, 0xff, 0x800);
	irq_waiting = false;
	scheduled_irq = 0;
}

void Machine::branch(bool cond, Instruction &inst) {
    if(cond) {
        inst.extra_cycles += 1;
        if ((inst.addr & 0xff00) != (pc & 0xff00)) {
            inst.extra_cycles += 1;
        }
        pc = inst.addr;
    }
}

void Machine::compare(byte a, byte b) {
    char sa = a;
    char sb = b;
    set_flag(N, (sa-sb) & (1 << 7));
    set_flag(Z, sa == sb);
    set_flag(C, a >= b);
}

void Machine::execute_inst() {
    byte m;
    byte a7, m7, r7;
    word result;
    switch(inst.op.op) {
    case NOP:
	case DOP:
    case TOP:
        break;
    case JMP:
        pc = inst.addr;
        break;
    case JSR:
        push2(pc-1);
        pc = inst.addr;
        break;
    case RTS:
        pc = pop2()+1;
        break;
    case RTI:
        p = (pop() | (1<<5)) & (~B);
        pc = pop2();
		if(get_flag(I))
			scheduled_irq = 0;
		else if(irq_waiting)
			scheduled_irq = 1;
        break;
    case BRK:
        pc += 1;
        p |= B;
        irq(); 
        break;
    case BCS:
        branch(get_flag(C), inst);
        break;
    case BCC:
        branch(!get_flag(C), inst);
        break;
    case BEQ:
        branch(get_flag(Z), inst);
        break;
    case BNE:
        branch(!get_flag(Z), inst);
        break;
    case BVS:
        branch(get_flag(V), inst);
        break;
    case BVC:
        branch(!get_flag(V), inst);
        break;
    case BPL:
        branch(!get_flag(N), inst);
        break;
    case BMI:
        branch(get_flag(N), inst);
        break;
    case BIT:
        m = inst.operand;
        set_flag(N, m & (1 << 7));
        set_flag(V, m & (1 << 6));
        set_flag(Z, (m & a) == 0);
        break;
    case CMP:
        compare(a, inst.operand);
        break;
    case CPY:
        compare(y, inst.operand);
        break;
    case CPX:
        compare(x, inst.operand);
        break;
    case CLC:
        set_flag(C, false);
        break;
    case CLD:
        set_flag(D, false);
        break;
    case CLV:
        set_flag(V, false);
        break;
    case CLI:
        set_flag(I, false);
        break;
    case SED:
        set_flag(D, true);
        break;
    case SEC:
        set_flag(C, true);
        break;
    case SEI:
        set_flag(I, true);
        break;
    case LDA:
        a = inst.operand;
        set_nz(a);
        break;
    case STA:
        set_mem(inst.addr, a);
        break;
    case LDX:
        x = inst.operand;
        set_nz(x);
        break;
    case STX:
        set_mem(inst.addr, x);
        break;
    case LDY:
        y = inst.operand;
        set_nz(y);
        break;
    case STY:
        set_mem(inst.addr, y);
        break;
    case LAX:
        a = inst.operand;
        x = inst.operand;
        set_nz(a);
        break;
    case SAX:
        set_mem(inst.addr, a & x);
        break;
    case PHP:
        push(p | B);
        break;
    case PLP:
        p = (pop() | (1 << 5)) & (~B);
        break;
    case PLA:
        a = pop();
        set_nz(a);
        break;
    case PHA:
        push(a);
        break;
    case AND:
        a &= inst.operand;
        set_nz(a);
        break;
	case AAC:
		a &= inst.operand;
		set_nz(a);
		set_flag(C, a & 0x80);
		break;
    case ORA:
        a |= inst.operand;
        set_nz(a);
        break;
    case EOR:
        a ^= inst.operand;
        set_nz(a);
        break;
    case ADC:
        a7 = a & (1 << 7);
        m7 = inst.operand & (1 << 7);
        result = a + inst.operand;
        if(get_flag(C)) {
            result += 1;
        }
        a = result & 0xff;
        set_flag(C, result > 0xff);
        set_nz(a);
        r7 = a & (1 << 7);
        set_flag(V, !((a7 != m7) || ((a7 == m7) && (m7 == r7))));
        break;
    case SBC:
        a7 = a & (1 << 7);
        m7 = inst.operand & (1 << 7);
        result = a - inst.operand;
        if(!get_flag(C)) {
            result -= 1;
        }
        a = result & 0xff;
        set_flag(C, result < 0x100);
        set_nz(a);
        r7 = a & (1 << 7);
        set_flag(V, !((a7 == m7) || ((a7 != m7) && (r7 == a7))));
        break;
    case INX:
        x += 1;
        set_nz(x);
        break;
    case INY:
        y += 1;
        set_nz(y);
        break;
    case DEX:
        x -= 1;
        set_nz(x);
        break;
    case DEY:
        y -= 1;
        set_nz(y);
        break;
    case INC:
        inst.operand += 1;
        inst.operand &= 0xff;
        set_nz(inst.operand);
        set_mem(inst.addr, inst.operand);
        break;
    case DEC:
        inst.operand -= 1;
        inst.operand &= 0xff;
        set_nz(inst.operand);
        set_mem(inst.addr, inst.operand);
        break;
    case DCP:
        set_mem(inst.addr, (inst.operand -1) & 0xff);
        compare(a, (inst.operand-1)&0xff);
        break;
    case ISB:
        inst.operand = (inst.operand + 1) & 0xff;
        set_mem(inst.addr, inst.operand);
		a7 = a & (1 << 7);
        m7 = inst.operand & (1 << 7);
        result = a - inst.operand;
        if(!get_flag(C)) {
            result -= 1;
        }
        a = result & 0xff;
        set_flag(C, result < 0x100);
        set_nz(a);
        r7 = a & (1 << 7);
        set_flag(V, !((a7 == m7) || ((a7 != m7) && (r7 == a7))));
        break;
    case LSR_A:
        set_flag(C, a & 1);
        a >>= 1;
        set_nz(a);
        break;
    case LSR:
        set_flag(C, inst.operand & 1);
        inst.operand >>= 1;
        set_mem(inst.addr, inst.operand);
        set_nz(inst.operand);
        break;
    case ASL_A:
        set_flag(C, a & (1 << 7));
        a <<= 1;
        set_nz(a);
        break;
    case ASL:
        set_flag(C, inst.operand & (1 << 7));
        inst.operand <<= 1;
        set_mem(inst.addr, inst.operand);
        set_nz(inst.operand);
        break;
	case ASR:
		a &= inst.operand;
		set_flag(C, a & 1);
		a >>= 1;
		set_nz(a);
		break;
	case ARR:
		a &= inst.operand;
		a >>= 1;
		if(get_flag(C))
			a |= 0x80;
		set_flag(C, a & (1<<6));
		set_flag(V, ((a & (1<<5))<<1)  ^ (a & (1<<6)));
		set_nz(a);
		break;
    case TSX:
        x = s;
        set_nz(x);
        break;
    case TXS:
        s = x;
        break;
    case TYA:
        a = y;
        set_nz(a);
        break;
    case TXA:
        a = x;
        set_nz(a);
        break;
	case ATX:
		a |= 0xff;
		a &= inst.operand;
		x = a;
		set_nz(x);
		break;
	case AXS:
		x = a & x;
		result = x - inst.operand;
		set_flag(C, result < 0x100);
		x = result & 0xff;
		set_nz(x);
		break;
	case SYA:
		m = y & (inst.args[1] + 1);
		if(!inst.extra_cycles)
			set_mem(inst.addr, m);
		break;
	case SXA:
		m = x & (inst.args[1] + 1);
		if(!inst.extra_cycles)
			set_mem(inst.addr, m);
		break;
    case ROR_A:
        m = a & 1;
        a >>= 1;
        if(get_flag(C))
            a |= 1 << 7;
        set_flag(C, m);
        set_nz(a);
        break;
    case ROR:
        m = inst.operand & 1;
        inst.operand >>= 1;
        if(get_flag(C))
            inst.operand |= 1 << 7;
        set_flag(C, m);
        set_mem(inst.addr, inst.operand);
        set_nz(inst.operand);
        break;
    case ROL_A:
        m = a & (1 << 7);
        a <<= 1;
        if(get_flag(C))
            a |= 1;
        set_flag(C, m);
        set_nz(a);
        break;
    case ROL:
        m = inst.operand & (1 << 7);
        inst.operand <<= 1;
        if(get_flag(C))
            inst.operand |= 1;
        set_flag(C, m);
        set_mem(inst.addr, inst.operand);
        set_nz(inst.operand);
        break;
    case TAY:
        y = a;
        set_nz(y);
        break;
    case TAX:
        x = a;
        set_nz(x);
        break;
    case RLA:
        m = inst.operand & (1 << 7);
        inst.operand <<= 1;
        if(get_flag(C))
            inst.operand |= 1;
        set_flag(C, m);
        set_mem(inst.addr, inst.operand);
        a &= inst.operand;
        set_nz(a);
        break;
    case SLO:
        set_flag(C, inst.operand & (1 << 7));
        inst.operand <<= 1;
        set_mem(inst.addr, inst.operand);
        a |= inst.operand;
        set_nz(a);
        break;
	case SRE:
		set_flag(C, inst.operand & 1);
        inst.operand >>= 1;
        set_mem(inst.addr, inst.operand);
        a ^= inst.operand;
        set_nz(a);
		break;
    case RRA:
        m = inst.operand & 1;
        inst.operand >>= 1;
        if(get_flag(C))
            inst.operand |= 1 << 7;
        set_mem(inst.addr, inst.operand);
		a7 = a & (1 << 7);
        m7 = inst.operand & (1 << 7);
        result = a + inst.operand;
        if(m) {
            result += 1;
        }
        a = result & 0xff;
        set_flag(C, result > 0xff);
        set_nz(a);
        r7 = a & (1 << 7);
        set_flag(V, !((a7 != m7) || ((a7 == m7) && (m7 == r7))));
		break;
    case XAA:
    case AXA:
    case XAS:
    case LAR:
        break;
    default:
        cout << "Unsupported opcode! " << int(inst.opcode) << endl;
        cout << inst.op.op << endl;
		cout << opnames[inst.op.op] << endl;
        throw new runtime_error("Unsupported opcode");
        break;
    }

    cycle_count += inst.op.cycles + inst.extra_cycles;
}

void Machine::run() {
    reset();
    ofstream cout("LOG.TXT");
	cout << uppercase << setfill('0');
    //debug = true;
    while(1) {
        try {
            if(debug)
                cout << HEX4(pc) << "  ";
            inst.next_instruction();
            if(debug)
                cout << inst << dump_regs() << endl; 
            execute_inst();
			if(irq_waiting && !get_flag(I) && !scheduled_irq) {
				cout << " scheduling IRQ " << endl;
				scheduled_irq = 2;
				irq_waiting = false;
			}
			if(scheduled_irq) {
				cout << "decrementing schedule " << scheduled_irq << endl;
				scheduled_irq--;
				if(!scheduled_irq)
					irq();
			}
			ppu->run();
			apu->update(inst.op.cycles + inst.extra_cycles);

			//special handling for blargg tests
			if(rom->prg_ram[1] == 0xde && rom->prg_ram[2] == 0xb0) {//&& mem[0x6003] == 0x61) {
				switch(rom->prg_ram[0]) {
				case 0x80:
					//running
					break;
				case 0x81:
					//need reset
					break;
				default:
					cout << "test done: " << endl;
					cout << (char*)(rom->prg_ram + 4) << endl;
					//cin.get();
					break;
				}
			}
        } catch(...) {
            break;
        }
    }
}

