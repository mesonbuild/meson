/* File : example.cxx */

#include "example.h"
#include <stdio.h>

Pi::Pi(int _iterations) : iterations(_iterations) {}

// pi/4 = 1 - 1/3 + 1/5 - 1/7 + 1/9 - 1/11 + 1/13 - 1/15 + 1/17..
// (a very slow method of finding Pi)
double Pi::approx() {
    double sum = 0;
    for (int i = 0; i < iterations; i++) {
      sum += (1.0 / (1.0 + 2.0 * i)) * (i % 2 == 0 ? 1.0 : -1.0);
    }
    return sum * 4;
}

// Using pointers with async
Pi *calc(Pi *engine, double *result) {
    *result = engine->approx();

    return engine;
}
