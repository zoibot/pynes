#include <iostream>

#include <SFML/Audio.hpp>

#include "util.h"

using namespace std;

class Pulse {
    byte duty_cycle;
    bool length_halt;
    byte envelope;
    word timer;
    byte length_load;
public:
    void enable(bool en);
    void write_register(byte num, byte val);
    byte read_register(byte num);
};

class Triangle {
public:
    void enable(bool en);
    void write_register(byte num, byte val);
    byte read_register(byte num);
};

class Noise {
public:
    void enable(bool en);
    void write_register(byte num, byte val);
    byte read_register(byte num);
};

class DMC {
public:
    void enable(bool en);
    void write_register(byte num, byte val);
    byte read_register(byte num);
};

class APU {
    sf::SoundBuffer buf;
    sf::Sound sound;
    Pulse p1, p2;
    Triangle tr;
    Noise ns;
    DMC dmc;
    bool frame_mode;
    bool frame_irq;
    byte status;
public:
    APU();
    void write_register(byte num, byte val);
    byte read_register(byte num);
    void update(int cycles);
};