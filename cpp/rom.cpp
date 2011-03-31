#include <cstring>
#include <cstdlib>

#include "rom.h"
#include "mapper.h"
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
    cout << (flags7 &0xf) << endl;
    if((flags7 & 0xf) == 0x8)
        cout << "ines 2" << endl;
    mapper_num = ((flags6 & 0xf0) >> 4) | (flags7 & 0xf0);
	switch(mapper_num) {
	case 0:
		mapper = new NROM(this);
		break;
	case 2:
		mapper = new UNROM(this);
		break;
	default:
		cout << "Unsupported Mapper" << endl;
        cout << int(mapper_num) << endl;
        exit(1);
		break;
	}
	cout << "Using mapper: " << int(mapper_num) << " " << mapper->name() << endl;
    prg_ram_size = header[8];
    if(flags6 & (1<<2)) {
        cout << "loading trainer" << endl;
        f.read((char*)trainer, 512);
    }
	prg_banks = new byte[prg_size * 0x4000];
	f.read((char*)prg_banks, prg_size * 0x4000);
	chr_banks = new byte[chr_size * 0x2000];
	if(chr_size != 0)
		f.read((char*)chr_banks, chr_size * 0x2000);
	prg_rom = new byte*[2];
	prg_rom[0] = prg_banks;
	prg_rom[1] = prg_banks + (prg_size - 1) * 0x4000;
	chr_rom = new byte*[2];
	chr_rom[0] = chr_banks;
	chr_rom[1] = chr_banks + 0x1000;
    //flags9,flags10
    cout << "prg size " << int(prg_size) << endl;
    cout << "chr size " << int(chr_size) << endl;
    if(!prg_ram_size) {
        prg_ram = new byte[8192];
        memset(prg_ram, 0xff, 0x2000);
    } else {
        prg_ram = new byte[8192 * prg_ram_size];
        memset(prg_ram, 0xff, 0x2000 * prg_ram_size);
    }
    cout << "Rom loaded successfully!" << endl;

}
