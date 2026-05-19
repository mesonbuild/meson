#import <Foundation/Foundation.h>

#import "Library-Swift.h"

int main()
{
    TestObject *obj = [[TestObject alloc] init];

    if (![[obj callMeWithInput: @"To Swift"] isEqualToString: @"To Swift, and back"]) {
        fprintf(stderr, "got wrong return value\n");
        abort();
    }

    [obj release];
}
