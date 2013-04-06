#import<Foundation/NSString.h>

int main(int argc, char **argv) {
  int result;
  NSString *str = [NSString new];
  result = [str length];
  [str release];
  return result;
}

