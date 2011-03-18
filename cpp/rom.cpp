#include <cstring>

#include "rom.h"
#include "util.h"

using namespace std;

Rom::Rom(istream& f) {
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
    prg_ram_size = header[8];
    if(flags6 & (1<<2)) {
        cout << "loading trainer" << endl;
        f.read((char*)trainer, 512);
    }
    //flags9,flags10
    prg_rom = new byte[16384 * prg_size];
    f.read((char*)prg_rom, 16384 * prg_size);
    cout << int(prg_size) << endl;
    bool chr_ram = (chr_size == 0);
    if(chr_ram) {
        chr_rom = new byte[8192];
    } else {
        chr_rom = new byte[8192 * chr_size];
        f.read((char*)chr_rom, 8192 * chr_size);
    }
    if(!prg_ram_size) {
        prg_ram = new byte[8192];
    } else {
        prg_ram = new byte[8192 * prg_ram_size];
    }
	cout << "Rom loaded successfully!" << endl;

}
