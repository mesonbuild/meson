extern void f(void);
extern void g(void);
extern void h(void);
extern void undefined(void);

/* No extern here to get a common symbol */
void (*p)(void);
