#include <string>
using namespace std;

class Machine;

class Instruction {
    void next_instruction();
    Machine *mach;

    char opcode;
    short operand;
    bool store;
    bool illegal;
    string op;
}
