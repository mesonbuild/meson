import QtQuick 2.0
import Foo.Bar 1.0

Window {
    width: 640
    height: 200
    visible: true
    title: qsTr("Sample")

    QmlCppExposed {
        id: cppExposed
    }
    Text {
        id: cppExposedTxt
        text: "value from Cpp exposed " +  cppExposed.foo + " (should be 42)"
    }
    Text {
        id: singletonTxt
        anchors.top: cppExposedTxt.bottom
        text: "value from Singleton exposed " +  QmlSingleton.myprop + " (should be 51)"
    }
    QmlOtherStuff {
        anchors.top: singletonTxt.bottom
    }

}
