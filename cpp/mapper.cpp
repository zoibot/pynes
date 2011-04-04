#include "mapper.h"
#include "rom.h"

Mapper::Mapper(Rom *rom) {
	this->rom = rom;
}

NROM::NROM(Rom *rom) : Mapper(rom) {
}

void NROM::prg_write(word addr, byte val) {};
void NROM::load_prg(int prg_size) {
	rom->prg_rom[0] = rom->prg_banks;
	rom->prg_rom[1] = rom->prg_banks + 0x4000 * (prg_size - 1);
}
void NROM::load_chr() {
	rom->chr_rom[0] = rom->chr_banks;
	rom->chr_rom[1] = rom->chr_banks + 0x1000;
}
string NROM::name() {
	return "NROM";
};

UNROM::UNROM(Rom *rom) : Mapper(rom) {
	this->rom = rom;
}
void UNROM::prg_write(word addr, byte val) {
	bank = val & 7;
	rom->prg_rom[0] = rom->prg_banks + (0x4000 * bank);
};
void UNROM::load_prg(int prg_size) {
	rom->prg_rom[0] = rom->prg_banks;
	rom->prg_rom[1] = rom->prg_banks + (prg_size - 1) * 0x4000;
}
void UNROM::load_chr() {
	rom->chr_rom[0] = rom->chr_banks;
	rom->chr_rom[1] = rom->chr_banks + 0x1000;
}
string UNROM::name() {
	return "UNROM";
};

CNROM::CNROM(Rom *rom) : Mapper(rom) {
}
void CNROM::prg_write(word addr, byte val) {
	rom->chr_rom[0] = rom->chr_banks + (0x2000 * (val & 3));
	rom->chr_rom[1] = rom->chr_banks + (0x2000 * (val & 3)) + 0x1000;
};
void CNROM::load_prg(int prg_size) {
	rom->prg_rom[0] = rom->prg_banks;
	rom->prg_rom[1] = rom->prg_banks;
	if(prg_size > 1) {
		rom->prg_rom[1] += 0x4000;
	}
}
void CNROM::load_chr() {
	rom->chr_rom[0] = rom->chr_banks;
	rom->chr_rom[1] = rom->chr_banks + 0x1000;
}
string CNROM::name() {
	return "CNROM";
};

MMC1::MMC1(Rom *rom) : Mapper(rom) {
	control = 0xc;
	load = 0;
	shift = 0;
	prg_bank = 0;
}
void MMC1::prg_write(word addr, byte val) {
	load |= (val & 1) << shift;
	shift += 1;
	if(val & 0x80) {
		load = 0;
		shift = 0;
		control |= 0xc;
		return;
	}
	if(shift == 5) {
		if(addr < 0xa000) {
			switch(load & 3) {
			case 0:
				rom->mirror = SINGLE_LOWER;
				break;
			case 1:
				rom->mirror = SINGLE_UPPER;
				break;
			case 2:
				rom->mirror = VERTICAL;
				break;
			case 3:
				rom->mirror = HORIZONTAL;
				break;
			}
			if((control & 0xc) != (load & 0xc)) {
				control = load;
				update_prg_bank();
			}
			control = load;
		} else if(addr < 0xc000) {
			cout << "switching char bank" << endl;
			//chr bank 0
			if(control & (1<<5)) {
				//4kb mode
				rom->chr_rom[0] = rom->chr_banks + 0x1000 * load;
			} else {
				rom->chr_rom[0] = rom->chr_banks + 0x1000 * (load & 0x1e);
				rom->chr_rom[1] = rom->chr_banks + 0x1000 * (load | 1);
			}
		} else if(addr < 0xe000) {
			cout << "switching char bank" << endl;
			//chr bank 1
			if(control & (1<<5)) {
				//4kb mode
				rom->chr_rom[1] = rom->chr_banks + 0x1000 * load;
			} else {
				//8kb ignore
			}
		} else {
			//prg bank
			prg_bank = load;
			update_prg_bank();
		}
		shift = 0;
		load = 0;
	}
};
void MMC1::update_prg_bank() {
	switch(control & 0xc) {
		case 0:
		case 4:
			cout << (prg_bank & 0xe) << " " << ((prg_bank & 0xe) | 1) << endl;
			rom->prg_rom[0] = rom->prg_banks + 0x4000 * (prg_bank & 0xe);
			rom->prg_rom[1] = rom->prg_banks + 0x4000 * ((prg_bank & 0xe) | 1);
			break;
		case 0x8:
			rom->prg_rom[0] = rom->prg_banks;
			rom->prg_rom[1] = rom->prg_banks + 0x4000 * prg_bank;
			break;
		case 0xc:
			rom->prg_rom[0] = rom->prg_banks + 0x4000 * prg_bank;
			rom->prg_rom[1] = rom->prg_banks + 0x4000 * (rom->prg_size - 1);
			break;
	}
}

void MMC1::load_prg(int prg_size) {
	rom->prg_rom[0] = rom->prg_banks;
	rom->prg_rom[1] = rom->prg_banks + 0x4000 * (rom->prg_size - 1);
}
void MMC1::load_chr() {
	rom->chr_rom[0] = rom->chr_banks;
	rom->chr_rom[1] = rom->chr_banks + 0x1000;
}
string MMC1::name() {
	return "MMC1";
};

AXROM::AXROM(Rom *rom) : Mapper(rom) {
}
void AXROM::prg_write(word addr, byte val) {
	rom->prg_rom[0] = rom->prg_banks + 0x8000 * (val & 7);
	rom->prg_rom[1] = rom->prg_banks + 0x8000 * (val & 7) + 0x4000;
	if(val & 0x10) {
		rom->mirror = SINGLE_LOWER;
	} else {
		rom->mirror = SINGLE_UPPER;
	}
};
void AXROM::load_prg(int prg_size) {
	rom->prg_rom[0] = rom->prg_banks;
	rom->prg_rom[1] = rom->prg_banks + 0x4000;// * (prg_size - 1);
}
void AXROM::load_chr() {
	rom->chr_rom[0] = rom->chr_banks;
	rom->chr_rom[1] = rom->chr_banks + 0x1000;
}
string AXROM::name() {
	return "AxROM";
};
