#!/bin/sh
g++ -g -c -o main.o main.cpp
g++ -g -c -o ppu.o ppu.cpp
g++ -g -c -o machine.o machine.cpp
g++ -g -c -o rom.o rom.cpp
g++ -g -c -o mapper.o mapper.cpp
g++ -g -c -o apu.o apu.cpp
g++ -g -c -o instruction.o instruction.cpp

g++ *.o -o nes -Wall -lsfml-system -lsfml-graphics -lsfml-window -lsfml-audio 
