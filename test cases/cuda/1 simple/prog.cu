#include <stdio.h>
#include <iostream>

__global__ void kernel (void){

}

int main( void ) {
      kernel<<<1,1>>>();
      printf( "Hello, World!\n" ); 
      return 0;
}

