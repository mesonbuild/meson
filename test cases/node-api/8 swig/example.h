/* File : example.h */

// A class that can be used to compute Pi
class Pi {
  int iterations;
public:
  Pi(int);
  double approx();
};

// A global function that returns its value in an argument
Pi *calc(Pi *, double *result);
