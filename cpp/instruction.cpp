#include "instruction.h"
#include "machine.h"

Opcode::Opcode() {
	this->invalid = true;
}

Opcode::Opcode(Op op, AddrMode amode, int cycles) {
	this->op = op;
	this->addr_mode = amode;
	this->cycles = cycles;
    this->extra_page_cross = 1;
	if(op == STA || op == STX || op == STY)
		store = true;
}

Opcode::Opcode(Op op, AddrMode amode, int cycles, int extra_page_cross) { 
	this->op = op;
	this->addr_mode = amode;
	this->cycles = cycles;
	if(op == STA || op == STX || op == STY)
		store = true;
    this->extra_page_cross = extra_page_cross;
}

Instruction::Instruction() {
	arglen = 0;
}

ostream& operator <<(ostream &out, Instruction &inst) {
	out << HEX2(inst.opcode);
	out << " ";
	if(inst.arglen > 0) {
		out << HEX2(inst.args[0]);
	} else {
		out << "  ";
	}
	out << " ";
	if(inst.arglen > 1) {
		out << HEX2(inst.args[1]);
	} else {
		out << "  ";
	}
	out << " ";
	if(inst.op.illegal) {
		out << "*";
	} else {
		out << " ";
	}
	out << opnames[inst.op.op];
	out << " ";
	switch (inst.op.addr_mode) {
	case IMM:
		out << "#$" << HEX2(inst.operand) << "                        ";
		break;
	case REL:
		out << "$" << HEX4(inst.addr) << "                       ";
		break;
	case ZP:
	case ZP_ST:
		out << "$" << HEX2(inst.addr) << "                         ";
		break;
	case ABS:
	case ABS_ST:
		out << "$" << HEX4(inst.addr) << "                       ";
		break;
    case A:
        out << "A" << "                           ";
        break;
    case ZPX:
        out << "($" << HEX2(inst.args[0]) << ",X) @ " << HEX2(inst.addr) << "                ";
        break;
	case ZPY:
        out << "($" << HEX2(inst.args[0]) << ",Y) @ " << HEX2(inst.addr) << "                ";
        break;
    case IDIX:
        out << "($" << HEX2(inst.args[0]) << "),Y     " << HEX2(inst.operand) << " @ " << HEX2(inst.i_addr) << "         ";
        break;
    case IXID:
        out << "($" << HEX2(inst.args[0]) << ",X) @ " << HEX2(inst.i_addr) << "                ";
        break;
	default:
		out << "                            ";
	}
	return out;
}

void Instruction::next_instruction() {
	char off;
	opcode = mach->next_byte();
	extra_cycles = 0;
	op = ops[opcode];
	switch (op.addr_mode) {
	case IMM:
		operand = mach->next_byte();
		args[0] = operand;
		arglen = 1;
		break;
	case ZP:
		addr = mach->next_byte();
		operand = mach->get_mem(addr);
		args[0] = addr;
		arglen = 1;
		break;
	case ZP_ST:
		addr = mach->next_byte();
		args[0] = addr;
		arglen = 1;
		break;
	case ABS:
		addr = mach->next_word();
		operand = mach->get_mem(addr);
		args[0] = addr & 0xff;
		args[1] = (addr & 0xff00) >> 8;
		arglen = 2;
		break;
	case ABS_ST:
		addr = mach->next_word();
		args[0] = addr & 0xff;
		args[1] = (addr & 0xff00) >> 8;
		arglen = 2;
		break;
	case ABSI:
		i_addr = mach->next_word();
    	addr = mach->get_mem(i_addr) + (mach->get_mem(((i_addr+1) & 0xff) | (i_addr & 0xff00)) << 8);
		args[0] = i_addr & 0xff;
		args[1] = (i_addr & 0xff00) >> 8;
		arglen = 2;
		break;
	case ABSY:
		i_addr = mach->next_word();
		addr = (i_addr + mach->y) & 0xffff;
		if(!op.store) {
			operand = mach->get_mem(addr);
		}
		if((i_addr & 0xff00) != (addr & 0xff00)) {
			extra_cycles += op.extra_page_cross;
		}
		args[0] = i_addr & 0xff;
		args[1] = (i_addr & 0xff00) >> 8;
		arglen = 2;
		break;
	case ABSX:
		i_addr = mach->next_word();
		addr = (i_addr + mach->x) & 0xffff;
		if(!op.store) {
			operand = mach->get_mem(addr);
		}
		if((i_addr & 0xff00) != (addr & 0xff00)) {
			extra_cycles += op.extra_page_cross;
		}
		args[0] = i_addr & 0xff;
		args[1] = (i_addr & 0xff00) >> 8;
		arglen = 2;
		break;
	case REL:
		off = mach->next_byte();
		addr = off + mach->pc;
		args[0] = off;
		arglen = 1;
		break;
	case IXID:
		args[0] = mach->next_byte();
		i_addr = (args[0] + mach->x) & 0xff;
		addr = (mach->get_mem(i_addr) + (mach->get_mem((i_addr+1) & 0xff) << 8));
		if(!op.store) {
			operand = mach->get_mem(addr);
		}
		arglen = 1;
		break;
	case IDIX:
		i_addr = mach->next_byte();
		addr = (mach->get_mem(i_addr) + (mach->get_mem((i_addr+1)&0xff)<<8)) + mach->y;
		addr &= 0xffff;
		if(!op.store) {
			operand = mach->get_mem(addr);
		}
		if((addr & 0xff00) != ((addr - mach->y) & 0xff00)) {
			extra_cycles += op.extra_page_cross;
		}
		args[0] = i_addr;
		arglen = 1;
		break;
	case ZPX:
		i_addr = mach->next_byte();
		addr = (i_addr + mach->x) & 0xff;
		if(!op.store) {
			operand = mach->get_mem(addr);
		}
		args[0] = i_addr;
		arglen = 1;
		break;
	case ZPY:
		i_addr = mach->next_byte();
		addr = (i_addr + mach->y) & 0xff;
		if(!op.store) {
			operand = mach->get_mem(addr);
		}
		args[0] = i_addr;
		arglen = 1;
		break;
	default:
		arglen = 0;
		break;
	}
}
