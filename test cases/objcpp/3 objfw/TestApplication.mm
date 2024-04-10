#import <ObjFW/ObjFW.h>

@interface TestApplication: OFObject <OFApplicationDelegate>
@end

OF_APPLICATION_DELEGATE(TestApplication)

@implementation TestApplication
- (void)applicationDidFinishLaunching: (OFNotification *)notification {
    [OFApplication terminate];
}
@end
