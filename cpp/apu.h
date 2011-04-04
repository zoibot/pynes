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
    bool length_enabled;
	byte length_counter;
public:
    void enable_length(bool en);
	void clock_length_counter();
	bool length_nonzero();
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
	bool frame_interrupt;
	int frame_cycles;
	byte sequencer_status;
	void clock_sequencer();
	int counter;
public:
    APU(Machine *mach);
    void write_register(byte num, byte val);
    byte read_register(byte num);
    void update(int cycles);
};

static const byte length_table[0x20] = { 10, 254, 20, 2, 40, 4, 80, 6, 160, 8, 60, 10, 14, 12, 26, 14, 12, 16, 24, 18, 48, 20, 96, 22, 192, 24, 72, 26, 16, 28, 32, 30 };

#endif //APU_H