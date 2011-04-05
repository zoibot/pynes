#ifndef MACHINE_H
#define MACHINE_H

#include <sstream>
#include <stdexcept>

#include <SFML/Graphics.hpp>
#include <SFML/Window.hpp>

#include "ppu.h"
#include "apu.h"
#include "instruction.h"
#include "rom.h"
#include "util.h"

const sf::Key::Code keymap[8] = { 
                  sf::Key::Z, //a
                  sf::Key::X, //b
                  sf::Key::S, //Select
                  sf::Key::Return, //Start
                  sf::Key::Up,
                  sf::Key::Down,
				  sf::Key::Left,
                  sf::Key::Right,
                };

class Machine {
    byte *mem;
    Instruction inst;
	bool irq_waiting;
	int scheduled_irq;
    //ppu
    PPU *ppu;
    sf::RenderWindow wind;
    //APU
    APU *apu;
    //sound??
    //input
    byte read_input_state;
    bool keys[8];
    //flags
    static const byte N = 1 << 7;
    static const byte V = 1 << 6;
    static const byte B = 1 << 4;
    static const byte D = 1 << 3;
    static const byte I = 1 << 2;
    static const byte Z = 1 << 1;
    static const byte C = 1 << 0;

    void set_flag(byte flag, bool val);
    bool get_flag(byte flag);
    void set_nz(byte val);

	void branch(bool cond, Instruction &inst);
	void compare(byte a, byte b);

    void push2(word val);
    word pop2();
    void push(byte val);
    byte pop();

	void irq();

    string dump_regs();

public:
    Machine(Rom *rom);
	bool debug;
	int testeroo;
	   
	int pc;
    byte a, s, p;
	byte x, y;
	int cycle_count;
	Rom *rom;

    void reset();
    void nmi(word addr);
	void request_irq();
    void execute_inst();
    void run();
    void save();

	byte get_mem(word addr);
    byte get_code_mem(word addr);
    void set_mem(word addr, byte val);

	byte next_byte();
    word next_word();

};

#endif //MACHINE_H
