#include <iostream>
/* Class for reading iNES files */
class Rom {
    char prg_size, ch_size;
    char flags6, flags7;
    char trainer[512];
    char* prg_rom;
    char* chr_rom;
    char* prg_ram;

    Rom(istream f);
}
