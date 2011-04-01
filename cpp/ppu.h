#ifndef PPU_H
#define PPU_H

#include <list>

#include <SFML/Window.hpp>
#include <SFML/Graphics.hpp>

#include "util.h"

class Machine;

struct Sprite {
    byte y;
    byte tile;
    byte attrs;
    byte x;
};

struct NameTable {
};

struct PatternTables {
};

struct Palette {
};

class PPU {
private:
	bool debug_flag;
    Machine *mach;
    sf::RenderWindow *wind;
    sf::Image screen;
	sf::RenderWindow debug;
	sf::Image debugi;
	int cycle_count;
    //memory
    byte* mem;
    byte mem_buf;
    word* mirror_table;
    bool latch;
    byte pmask;
    byte pstat;
    byte pctrl;
    //position
    byte xoff, fine_x;
    list<Sprite*> cur_sprs;
    //helpers
    void do_vblank(bool rendering_enabled);
    void render_pixels(byte x, byte y, byte num);
    void new_scanline();
    void draw_frame();
    byte get_mem_mirrored(word addr);
    void set_mirror(word from, word to, word size);
	NTMirroring current_mirroring;
public:
	int last_vblank_start;
	int last_vblank_end;
	word vaddr, taddr;
    word next_taddr;
    int sl;
    word cyc;
    byte* obj_mem;
    word obj_addr;
	void dump_nts();
    void run();
	void set_mirroring(NTMirroring mirror);
    void write_register(byte num, byte val);
    byte read_register(byte num);
    byte get_mem(word addr);
    void set_mem(word addr, byte val);
    PPU(Machine* mach, sf::RenderWindow* wind);
};

#endif //PPU_H
