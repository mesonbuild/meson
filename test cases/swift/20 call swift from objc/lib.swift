import Foundation

@objc
public class TestObject: NSObject {
    @objc
    public func callMe(input: String) -> String {
        return "\(input), and back"
    }
}
