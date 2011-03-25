#include "apu.h"
//sound queue??
APU::APU() {
    sound.SetBuffer(buf);
}

void APU::write_register(byte num, byte val) {
    switch(num) {

    default:
        break;
    }
}

byte APU::read_register(byte num) {
    switch(num) {
    default:
        return 0;
    }

}