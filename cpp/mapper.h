#ifndef MAPPER_H
#define MAPPER_H

#include "util.h"

struct Rom;

//abstract Mapper class
class Mapper {
public:
	Rom *rom;
	virtual void prg_write(word addr, byte val) = 0;
	virtual void load_prg(byte prg_size, istream& f) = 0;
	virtual void load_chr(byte chr_size, istream& f) = 0;
	virtual string name() = 0;
	Mapper(Rom *rom);
};

class NROM : public Mapper {
public:
	void prg_write(word addr, byte val);
	void load_prg(byte prg_size, istream& f);
	void load_chr(byte chr_size, istream& f);
	string name();
	NROM(Rom *rom);
};

class UNROM : public Mapper {
public:
	int bank;
	void prg_write(word addr, byte val);
	void load_prg(byte prg_size, istream& f);
	void load_chr(byte chr_size, istream& f);
	string name();
	UNROM(Rom *rom);
};

class CNROM : public Mapper {
public:
	void prg_write(word addr, byte val);
	void load_prg(byte prg_size, istream& f);
	void load_chr(byte chr_size, istream& f);
	string name();
	CNROM(Rom *rom);
};


#endif //MAPPER _H