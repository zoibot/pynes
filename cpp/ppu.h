#ifndef PPU_H
#define PPU_H

#include <SFML/Window.hpp>
#include <SFML/Graphics.hpp>

#include "util.h"

class Machine;

struct Sprite {
	byte y, tile, attrs, x;
};

struct NameTable {
};

struct PatternTables {
};

struct Palette {
};

class PPU {
private:
	Machine *mach;
	sf::RenderWindow *wind;
	sf::Image screen;
	//memory
	byte* mem;
	byte mem_buf;
	word* mirror_table;
	bool latch;
	byte* obj_mem;
	word obj_addr;
	byte pmask;
	byte pstat;
	byte pctrl;
	word vaddr, taddr;
	//position
	byte sl;
	word cyc;
	byte xoff, fine_x;
	int cycle_count;
	void do_vblank(bool rendering_enabled);
	void render_pixels(byte x, byte y, byte num);
	void new_scanline();
	void draw_frame();
	byte get_mem_mirrored(word addr);
	
public:
    void run();
	void write_register(byte num, byte val);
	byte read_register(byte num);
	byte get_mem(word addr);
	void set_mem(word addr, byte val);
	PPU(Machine* mach, sf::RenderWindow* wind);
};

#endif //PPU_H