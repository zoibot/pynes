#include <cstring>
#include <cstdlib>

#include "rom.h"
#include "util.h"

using namespace std;

Rom::Rom(istream& f) {
    //TODO: need a real mapper class
    byte header[16];
    f.read((char*)header, 16);
    if (strncmp((char*)header, "NES\x1a", 4) == 0) {
        cout << "header constant OK!" << endl;
    } else {
        cout << "bad rom...";
    }
    prg_size = header[4];
    chr_size = header[5];
    flags6 = header[6];
    flags7 = header[7];
    cout << (flags7 &0xf) << endl;
    if((flags7 & 0xf) == 0b1000)
        cout << "ines 2" << endl;
    mapper = ((flags6 & 0xf0) >> 4) | (flags7 & 0xf0);
    if(mapper != 0 && mapper != 2 && mapper != 3) {
        cout << "Unsupported Mapper" << endl;
        cout << int(mapper) << endl;
        exit(1);
    } else {
        cout << "Using mapper: " << int(mapper) << endl;
    }
    prg_ram_size = header[8];
    if(flags6 & (1<<2)) {
        cout << "loading trainer" << endl;
        f.read((char*)trainer, 512);
    }
    //flags9,flags10
    if(mapper == 0 || mapper == 64 || mapper == 3) {
        prg_rom = new byte[16384 * prg_size];
        f.read((char*)prg_rom, 16384 * prg_size);
    } else if(mapper == 2) {
        prg_rom = new byte[16384 * 2];
        prg_banks = new byte[16384 * prg_size];
        f.read((char*)prg_banks, 16384 * prg_size);
        memcpy(prg_rom, prg_banks, 16384);
        memcpy(prg_rom + 16384, prg_banks + (prg_size - 1) * 16384, 16384);
    }

    cout << "prg size " << int(prg_size) << endl;
    cout << "chr size " << int(chr_size) << endl;
    bool chr_ram = (chr_size == 0);
    if(chr_ram) {
        chr_rom = new byte[8192];
    } else {
        if(mapper == 0 || mapper == 64) {
            chr_rom = new byte[8192 * chr_size];
            f.read((char*)chr_rom, 8192 * chr_size);
        } else if(mapper == 3) {
            chr_banks = new byte[8192 * chr_size];
            f.read((char*)chr_banks, 8192 * chr_size);
            chr_rom = chr_banks;
        }
    }
    if(!prg_ram_size) {
        prg_ram = new byte[8192];
    } else {
        prg_ram = new byte[8192 * prg_ram_size];
    }
    cout << "Rom loaded successfully!" << endl;

}
