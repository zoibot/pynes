#ifndef APU_H
#define APU_H

#include <iostream>

#include <SFML/Audio.hpp>

#include "util.h"

using namespace std;

class Machine;

class Pulse {
    byte duty_cycle;
    bool length_halt;
    byte envelope;
    word timer;
    byte length_load;
public:
    //void enable(bool en);
    void write_register(byte num, byte val);
    byte read_register(byte num);
};

class Triangle {
public:
    //void enable(bool en);
    void write_register(byte num, byte val);
    byte read_register(byte num);
};

class Noise {
public:
   // void enable(bool en);
    void write_register(byte num, byte val);
    byte read_register(byte num);
};

class DMC {
public:
   // void enable(bool en);
    void write_register(byte num, byte val);
    byte read_register(byte num);
};

class APU {
	//implementation
    sf::SoundBuffer buf;
    sf::Sound sound;
	Machine *mach;
	//registers
	byte status;
	//channels
    Pulse p1, p2;
    Triangle tr;
    Noise ns;
    DMC dmc;
	//frame counter
    bool frame_mode;
	bool odd_clock;
    bool frame_irq;
	int frame_cycles;
	byte sequencer_status;
	void clock_sequencer();
public:
    APU(Machine *mach);
    void write_register(byte num, byte val);
    byte read_register(byte num);
    void update(int cycles);
};

#endif //APU_H