#include <cstring>

#include <rom.h>

using namespace std;

Rom::Rom(istream f) {
    char header[16];
    f.read(header, 16);
    if (strcmp(header, "NES\x1a") == 0) {
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
        f.read(trainer, 512);
    }
    //flags9,flags10
    prg_rom = new char[16384 * prg_size];
    f.read(prg_rom, 16384 * prg_size);
    cout << prg_size << endl;
    bool chr_ram = (chr_size == 0);
    if(chr_ram) {
        chr_rom = new char[8192];
    } else {
        chr_rom = new char[8192 * chr_size];
        f.read(chr_rom, 8192 * chr_size);
    }
    if(prg_ram_size) {
        prg_ram = new char[8192];
    } else {
        prg_ram = new char[8192 * prg_ram_size];
    }

}
