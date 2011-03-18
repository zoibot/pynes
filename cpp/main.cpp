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
	ifstream romf(argv[1], ifstream::binary | ifstream::in);
	Rom rom(romf);
	Machine mach(&rom);
	mach.run();

	cin.get();
    return 0;
}
