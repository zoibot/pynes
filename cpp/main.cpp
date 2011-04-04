#include <iostream>
#include <fstream>
#include <string>

using namespace std;

#include <SFML/Window.hpp>
#include <SFML/Graphics.hpp>
#include <SFML/System.hpp>

#include "machine.h"
#include "rom.h"


int main(int argc, char *argv[]) {
    if(argc < 2) {
        cout << "nope" << endl;
        exit(1);
    }
    bool debug = argc > 2;
    ifstream romf(argv[1], ifstream::binary | ifstream::in);
    cout << "Loading Rom: " << argv[1] << endl;
    Rom rom(romf, string(argv[1]));
    Machine mach(&rom);
	mach.debug = debug;
    mach.run();
    cin.get();
    return 0;
}
