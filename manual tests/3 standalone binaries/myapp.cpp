#include<SDL.h>
#include<memory>

int main(int argc, char **argv) {
  SDL_Surface *screenSurface;
  SDL_Event e;
  int keepGoing = 1;
  if(SDL_Init( SDL_INIT_VIDEO ) < 0) {
    printf( "SDL could not initialize! SDL_Error: %s\n", SDL_GetError() );
  }
  atexit(SDL_Quit);

  std::unique_ptr<SDL_Window, void(*)(SDL_Window*)> window(SDL_CreateWindow( "My application", SDL_WINDOWPOS_UNDEFINED, SDL_WINDOWPOS_UNDEFINED, 640, 480, SDL_WINDOW_SHOWN), SDL_DestroyWindow);
  screenSurface = SDL_GetWindowSurface(window.get());

  while(keepGoing) {
    while(SDL_PollEvent(&e) != 0) {
      if(e.type == SDL_QUIT) {
        keepGoing = 0;
        break;
      }
    }
    SDL_FillRect(screenSurface, NULL, SDL_MapRGB(screenSurface->format, 0xFF, 0x00, 0x00));
    SDL_UpdateWindowSurface(window.get());
    SDL_Delay(100);
  }

  return 0;
}
