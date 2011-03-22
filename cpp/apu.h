#include <SFML/Audio.hpp>

#include "util.h"

class Channel {
    enum Type {
        PULSE, TRIANGLE, NOISE
    } type;

}

class DMC {
}

class APU {
    sf::SoundBuffer buf;
    sf::Sound sound;
public:
    APU();
    void write_register(byte num, byte val);
    byte read_register(byte num);
    void update(int cycles);
}