#include "apu.h"
#include "machine.h"
//sound queue??

void Pulse::write_register(byte num, byte val) {
    switch(num % 4) {
    case 0:
        duty_cycle = (val & 0xc0) >> 6;
        length_halt = (val & 0x20);
        envelope = val & 0x1f;
        break;
    case 1:
        //sweep
        break;
    case 2:
        timer &= ~(0xf);
        timer |= val;
        break;
    case 3:
        length_load = (val & 0xf8) >> 3;
        timer &= ~(0x70);
        timer |= (val & 0x7) << 8;
        break;
    }
}
byte Pulse::read_register(byte num) {
    return 0;
}
void Triangle::write_register(byte num, byte val) {
}
byte Triangle::read_register(byte num) {
    return 0;
}
void Noise::write_register(byte num, byte val) {
}
byte Noise::read_register(byte num) {
    return 0;
}
void DMC::write_register(byte num, byte val) {
}
byte DMC::read_register(byte num) {
    return 0;
}

APU::APU(Machine *mach) {
	this->mach = mach;
	frame_cycles = 0;
	sequencer_status = 0;
	odd_clock = 0;
	frame_mode = 0;
	frame_irq = false;
	status = 0;
    sound.SetBuffer(buf);
}

void APU::write_register(byte num, byte val) {
    switch(num) {
    case 0x0:
    case 0x1:
    case 0x2:
    case 0x3:
        p1.write_register(num, val);
        break;
    case 0x4:
    case 0x5:
    case 0x6:
    case 0x7:
        p2.write_register(num, val);
    case 0x8:
    case 0x9:
    case 0xa:
    case 0xb:
        tr.write_register(num, val);
        break;
    case 0xc:
    case 0xd:
    case 0xe:
    case 0xf:
        ns.write_register(num, val);
        break;
    case 0x10:
    case 0x11:
    case 0x12:
    case 0x13:
        dmc.write_register(num, val);
    case 0x15:
        //status
        //length counter enable
        //val & 0x10 dmc something
        /*ns.enable(val & 0x8);
        tr.enable(val & 0x4);
        p2.enable(val & 0x2);
        p1.enable(val & 0x1);*/
        break;
    case 0x17:
        //frame counter
        frame_mode = val & 0x80;
        if(val & 0x40) {
            status &= ~0x40;
            frame_irq = false;
        }
        break;
    default:
        cout << "weird APU register " << num << endl;
        exit(1);
        break;
    }
}

byte APU::read_register(byte num) {
	byte old_status = status;
    switch(num) {
	case 0x15:
		status &= ~0x40;
		return old_status;
    case 0x17:
		return 0;
    default:
        return 0;
    }

}

void APU::update(int cycles) {
	frame_cycles += cycles;
	if((odd_clock && frame_cycles > 7,457) || frame_cycles > 7,458) {
		if(!odd_clock)
			frame_cycles -= 1;
		frame_cycles -= 7457;
		clock_sequencer();
		odd_clock = !odd_clock;
	}
}

void APU::clock_sequencer() {
	if(frame_mode) {
		sequencer_status = (sequencer_status + 1) % 5;
	} else {
		switch(sequencer_status) {
		case 0:
		case 2:
			//clock both
			break;
		case 3:
			//interrupt
			if(frame_irq) {
				status |= 0x40;
				mach->nmi(0xfffe);
				//other crap
			}
		case 1:
			//clock 1
			break;
		}
		sequencer_status = (sequencer_status + 1) % 4;
	}
}