import QtQuick
import My.Module1 as M1
import My.Module2 as M2
import My.Module3 as M3
import My.Module4 as M4

Item {

    M1.Basic { id: b1 }
    M1.Thing { id: t1  }
    M1.QmlCppExposed { id: c1 }

    M2.Thing { id: t2 }

    M3.Basic { id: b3 }

    M4.BasicAliased { id: b4 }

    Component.onCompleted: {
        function checkClass(display, id, value) {
            if (id.ok !== value) {
                console.log(display, "KO got", id.ok, "expected", value)
                Qt.exit(-1)
            }
            else
                console.log(display, "OK")
        }

        checkClass("M1.Basic", b1, 1);
        checkClass("M1.Thing", t1, 2);
        checkClass("M1.QmlCppExposed", c1, 3);
        checkClass("M1.QmlSingleton", M1.QmlSingleton, 5);

        checkClass("M2.Thing", t2, 2);

        checkClass("M3.Basic", b3, 1);

        checkClass("M4.BasicAliased", b4, 1);

        Qt.quit()
    }
}
