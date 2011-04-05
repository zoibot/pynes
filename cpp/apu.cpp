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
        length_counter = length_table[(val & 0xf8) >> 3];
        timer &= ~(0x70);
        timer |= (val & 0x7) << 8;
        break;
    }
}
byte Pulse::read_register(byte num) {
    return 0;
}
void Pulse::clock_length_counter() {
	if(!length_enabled) return;
	if(length_counter > 0)
		length_counter -= 1;
	if(length_counter == 0) {
		if(length_halt) {
			//do something
		}
	}
}
void Pulse::enable_length(bool en) {
	length_enabled = en;
	if(!length_enabled) {
		length_counter = 0;
	}
}
bool Pulse::length_nonzero() {
	return (length_counter > 0);
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
	frame_interrupt = false;
	frame_irq = false;
	status = 0;
    sound.SetBuffer(buf);
	counter = 0;
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
        tr.enable(val & 0x4);*/
        p2.enable_length(val & 0x2);
        p1.enable_length(val & 0x1);
        break;
    case 0x17:
        //frame counter
        frame_mode = val & 0x80;
        if(val & 0x40) {
			frame_interrupt = false;
            frame_irq = false;
        } else {
			frame_irq = true;
		}
        break;
    default:
        cout << "weird APU register " << num << endl;
        exit(1);
        break;
    }
}

byte APU::read_register(byte num) {
	byte old_status = 0;
    switch(num) {
	case 0x15:
		if(frame_interrupt)
			old_status |= 1<<6;
		if(p1.length_nonzero())
			old_status |= 1;
		if(p2.length_nonzero())
			old_status |= 2;
		frame_interrupt = false;
		return old_status;
    case 0x17:
		return 0;
    default:
        return 0;
    }

}

void APU::update(int cycles) {
	frame_cycles += cycles;
	if(p1.length_nonzero())
		counter += cycles;
	if((odd_clock && frame_cycles > 7457) || frame_cycles > 7458) {
		if(!odd_clock)
			frame_cycles -= 1;
		frame_cycles -= 7457;
		clock_sequencer();
		odd_clock = !odd_clock;
	}
	if(frame_interrupt)
		mach->request_irq();
}

void APU::clock_sequencer() {
	if(frame_mode) {
		switch(sequencer_status) {
		case 1:
		case 3:
			//clock both
			break;
		case 2:
		case 4:
			//clock 1
			break;
		}
		sequencer_status = (sequencer_status + 1) % 5;
	} else {
		switch(sequencer_status) {
		case 0:
		case 2:
			break;
		case 3:
			//interrupt
			if(frame_irq) {
				frame_interrupt = true;
				cout << "IRQ" << endl;
			}
		case 1:
			//clock 1
			p1.clock_length_counter();
			p2.clock_length_counter();
			break;
		}
		sequencer_status = (sequencer_status + 1) % 4;
	}
}
