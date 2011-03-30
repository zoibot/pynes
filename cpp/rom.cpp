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
	mapper->load_prg(prg_size, f);
	mapper->load_chr(chr_size, f);
    //flags9,flags10
    cout << "prg size " << int(prg_size) << endl;
    cout << "chr size " << int(chr_size) << endl;
    if(!prg_ram_size) {
        prg_ram = new byte[8192];
    } else {
        prg_ram = new byte[8192 * prg_ram_size];
    }
    cout << "Rom loaded successfully!" << endl;

}
