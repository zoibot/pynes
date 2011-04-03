#ifndef MAPPER_H
#define MAPPER_H

#include "util.h"

struct Rom;

//abstract Mapper class
class Mapper {
public:
	Rom *rom;
	virtual void prg_write(word addr, byte val) = 0;
	virtual void load_prg(int prg_size) = 0;
	virtual void load_chr() = 0;
	virtual string name() = 0;
	Mapper(Rom *rom);
};

class NROM : public Mapper {
public:
	void prg_write(word addr, byte val);
	void load_prg(int prg_size);
	void load_chr();
	string name();
	NROM(Rom *rom);
};

class UNROM : public Mapper {
public:
	int bank;
	void prg_write(word addr, byte val);
	void load_prg(int prg_size);
	void load_chr();
	string name();
	UNROM(Rom *rom);
};

class CNROM : public Mapper {
public:
	void prg_write(word addr, byte val);
	void load_prg(int prg_size);
	void load_chr();
	string name();
	CNROM(Rom *rom);
};

class MMC1 : public Mapper {
	byte load;
	byte control;
	byte shift;
	byte prg_bank;
	void update_prg_bank();
public:
	void prg_write(word addr, byte val);
	void load_prg(int prg_size);
	void load_chr();
	string name();
	MMC1(Rom *rom);
};

class AXROM : public Mapper {
public:
	void prg_write(word addr, byte val);
	void load_prg(int prg_size);
	void load_chr();
	string name();
	AXROM(Rom *rom);
};

#endif //MAPPER _H