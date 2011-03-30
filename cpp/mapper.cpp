#include "mapper.h"
#include "rom.h"

Mapper::Mapper(Rom *rom) {
	this->rom = rom;
}

NROM::NROM(Rom *rom) : Mapper(rom) {
}

void NROM::prg_write(word addr, byte val) {};
void NROM::load_prg(byte prg_size, istream& f) {
	rom->prg_banks = new byte[prg_size * 0x4000];
	f.read((char*)rom->prg_banks, prg_size * 0x4000);
	rom->prg_rom = new byte*[2];
	rom->prg_rom[0] = rom->prg_banks;
	rom->prg_rom[1] = rom->prg_banks;
}
void NROM::load_chr(byte chr_size, istream& f) {
	rom->chr_banks = new byte[chr_size * 0x2000];
	if(rom->chr_size != 0)
		f.read((char*)rom->chr_banks, chr_size * 0x2000);
	rom->chr_rom = new byte*[2];
	rom->chr_rom[0] = rom->chr_banks;
	rom->chr_rom[1] = rom->chr_banks + 0x1000;
}
string NROM::name() {
	return "NROM";
};

UNROM::UNROM(Rom *rom) : Mapper(rom) {
}
void UNROM::prg_write(word addr, byte val) {
	cout << "switching banks " << int(val) << " " << (0x4000 * (val & 7)) << " " << (int)rom->prg_size << endl;
	bank = val & 7;
	rom->prg_rom[0] = rom->prg_banks + (0x4000 * (val & 7));
	cout << (int)rom->prg_rom[0] << " " << (int)rom->prg_rom[0][0x3fff] << endl;
};
void UNROM::load_prg(byte prg_size, istream& f) {
	rom->prg_banks = new byte[prg_size * 0x4000];
	f.read((char*)rom->prg_banks, prg_size * 0x4000);
	rom->prg_rom = new byte*[2];
	rom->prg_rom[0] = rom->prg_banks;
	rom->prg_rom[1] = rom->prg_banks + (prg_size - 1) * 0x4000;
}
void UNROM::load_chr(byte chr_size, istream& f) {
	rom->chr_banks = new byte[chr_size * 0x2000];
	if(rom->chr_size != 0)
		f.read((char*)rom->chr_banks, chr_size * 0x2000);
	rom->chr_rom = new byte*[2];
	rom->chr_rom[0] = rom->chr_banks;
	rom->chr_rom[1] = rom->chr_banks + 0x1000;
}
string UNROM::name() {
	return "UNROM";
};

CNROM::CNROM(Rom *rom) : Mapper(rom) {
}
void CNROM::prg_write(word addr, byte val) {
	rom->prg_rom[0] = rom->prg_banks + (0x4000 * (val & 7));
};
void CNROM::load_prg(byte prg_size, istream& f) {
	rom->prg_banks = new byte[prg_size * 0x4000];
	f.read((char*)rom->prg_banks, prg_size * 0x4000);
	rom->prg_rom = new byte*[2];
	rom->prg_rom[0] = rom->prg_banks;
	rom->prg_rom[1] = rom->prg_banks;
}
void CNROM::load_chr(byte chr_size, istream& f) {
	rom->chr_banks = new byte[chr_size * 0x2000];
	if(rom->chr_size != 0)
		f.read((char*)rom->chr_banks, chr_size * 0x2000);
	rom->chr_rom = new byte*[2];
	rom->chr_rom[0] = rom->chr_banks;
	rom->chr_rom[1] = rom->chr_banks + 0x1000;
}
string CNROM::name() {
	return "CNROM";
};