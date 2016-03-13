#ifdef CTHING
#error "Local C argument set in wrong target"
#endif

#ifdef CPPTHING
#error "Local CPP argument set in wrong target"
#endif

int func() { return 0; }
