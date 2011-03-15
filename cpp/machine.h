#include <ppu.h>
#include <instruction.h>

const int keymap[8] = { sf::Key::Code.Left,
                  sf::Key::Code.Right,
                  sf::Key::Code.Up,
                  sf::Key::Code.Down,
                  sf::Key::Code.X, //b
                  sf::Key::Code.Z, //a
                  sf::Key::Code.Return, //Start
                  sf::Key::Code.S, //Select
                }

class Machine {
    int pc;
    char a, s, p;
    char x, y;
    char *mem;
    int cycle_count;
    Instruction inst;
    //ppu
    PPU *ppu;
    sf::RenderWindow wind;
    //APU
    //input
    char read_input_state = 0;
    bool keys[8];
    //flags
    const char N = 1 << 7;
    const char V = 1 << 6;
    const char B = 1 << 4;
    const char D = 1 << 3;
    const char I = 1 << 2;
    const char Z = 1 << 1;
    const char C = 1 << 0;

    void set_flag(char flag, bool val);
    bool get_flag(char flag);
    void set_nz(char val);

    char next_byte();
    char next_word();
    char get_mem(short addr);
    char get_code_mem(short addr);
    void set_mem(addr, val);

    void push2(val);
    short pop2();
    void push(val);
    char pop();

    string dump_regs();

    Machine(Rom *rom);

    void reset();
    void nmi();
    void execute_inst();
    void run();

}
