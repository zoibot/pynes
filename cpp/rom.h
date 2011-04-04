#ifndef ROM_H
#define ROM_H

#include <iostream>
using namespace std;
#include "util.h"
#include "mapper.h"
/* Class for reading iNES files */
struct Rom {
    byte prg_size, chr_size;
	byte prg_ram_size;
    byte flags6, flags7;
    byte mapper_num;
	Mapper *mapper;
    byte trainer[512];
    byte* prg_rom[2];
    byte* prg_banks;
    byte* chr_rom[2];
    byte* chr_banks;
    byte* prg_ram;
	NTMirroring mirror;
	string fname;

    Rom(istream& f, string fname);
};

#endif //ROM_H
