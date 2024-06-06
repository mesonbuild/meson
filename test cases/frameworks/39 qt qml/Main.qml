import QtQuick
import My.Module1 as M1

Item {
    id: root

    Component.onCompleted: {
        function checkInstance(label, instance, value) {
            if (!instance) {
                console.log(label, "KO instance is null")
                return false
            } if (instance.ok !== value) {
                console.log(label, "KO got", instance.ok, "expected", value)
                return false
            } else {
                console.log(label, "OK")
                return true
            }
        }

        function checkClass(namespace, classname, value) {
            let newObject = null;
            try {
                newObject = Qt.createQmlObject(
                    "import %1; %2 {}".arg(namespace).arg(classname),
                    root,
                    "some path"
                )
            } catch (e) {
                console.log(namespace, classname, "KO failed to instanciate object")
                return false
            }
            return checkInstance("%1 %2".arg(namespace).arg(classname), newObject, value)
        }

        let ret = true
        ret &= checkClass("My.Module1", "Basic", 1);
        ret &= checkClass("My.Module1", "Thing", 2);
        ret &= checkClass("My.Module1", "QmlCppExposed", 3);
        ret &= checkInstance("My.Module1 QmlSingleton", M1.QmlSingleton, 5)

        ret &= checkClass("My.Module2", "Thing", 2);
        ret &= checkClass("My.Module3", "Basic", 1);
        ret &= checkClass("My.Module4", "BasicAliased", 1);
        ret &= checkClass("My.Module5", "SubdirHeader", 6);
        ret &= checkClass("My.Module6", "Basic", 1);

        if (!ret)
            Qt.exit(1)
        else
            Qt.quit()
    }
}
