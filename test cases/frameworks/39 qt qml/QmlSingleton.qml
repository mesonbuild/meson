pragma Singleton
import QtQuick

Item {
    property alias ok: sub.ok

    Internal {
        id: sub
    }
}
