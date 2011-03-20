#ifndef ROM_H
#define ROM_H

#include <iostream>
using namespace std;
#include "util.h"
/* Class for reading iNES files */
struct Rom {
    byte prg_size, chr_size;
	byte prg_ram_size;
    byte flags6, flags7;
    byte mapper;
    byte trainer[512];
    byte* prg_rom;
    byte* prg_banks;
    byte* chr_rom;
    byte* chr_banks;
    byte* prg_ram;

    Rom(istream& f);
};

#endif //ROM_H
