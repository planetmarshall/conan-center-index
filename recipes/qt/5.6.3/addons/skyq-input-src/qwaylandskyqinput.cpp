#include "qt563logging.h"
/****************************************************************************
**
** Copyright © 2019 Sky UK.
**
****************************************************************************/

#include "ethannativeevent.h"
#include "qwaylandskyqinput.h"

#include <linux/input.h>
#include <QDebug>
#include <qpa/qwindowsysteminterface.h>
#include <QtGui/QGuiApplication>
#include <QtWaylandClient/private/qwaylanddisplay_p.h>

const QMap<int32_t, std::pair<int, QString>> QWaylandSkyQInput::mKeyMap = {
    {KEY_ESC, {Qt::Key_Escape, QStringLiteral("\[")}},
    {KEY_HOME, {Qt::Key_Home, QStringLiteral("")}},
    {KEY_END, {Qt::Key_End, QStringLiteral("")}},
    {KEY_ENTER, {Qt::Key_Return, QStringLiteral("\n")}},
    {KEY_UP, {Qt::Key_Up, QStringLiteral("")}},
    {KEY_DOWN, {Qt::Key_Down, QStringLiteral("")}},
    {KEY_LEFT, {Qt::Key_Left, QStringLiteral("")}},
    {KEY_RIGHT, {Qt::Key_Right, QStringLiteral("")}},
    {KEY_PAGEUP, {Qt::Key_PageUp, QStringLiteral("")}},
    {KEY_PAGEDOWN, {Qt::Key_PageDown, QStringLiteral("")}},
    {KEY_SCROLLUP, {Qt::Key_BracketLeft, QStringLiteral("")}},
    {KEY_SCROLLDOWN, {Qt::Key_BracketRight, QStringLiteral("")}},
    {KEY_DELETE, {Qt::Key_Delete, QStringLiteral("")}},
    {KEY_INSERT, {Qt::Key_Insert, QStringLiteral("")}},

    {KEY_KPASTERISK, {Qt::Key_Asterisk, QStringLiteral("*")}},
    {KEY_KPPLUS, {Qt::Key_Plus, QStringLiteral("+")}},
    {KEY_KPMINUS, {Qt::Key_Minus, QStringLiteral("-")}},

    {KEY_0, {Qt::Key_0, QStringLiteral("0")}},
    {KEY_1, {Qt::Key_1, QStringLiteral("1")}},
    {KEY_2, {Qt::Key_2, QStringLiteral("2")}},
    {KEY_3, {Qt::Key_3, QStringLiteral("3")}},
    {KEY_4, {Qt::Key_4, QStringLiteral("4")}},
    {KEY_5, {Qt::Key_5, QStringLiteral("5")}},
    {KEY_6, {Qt::Key_6, QStringLiteral("6")}},
    {KEY_7, {Qt::Key_7, QStringLiteral("7")}},
    {KEY_8, {Qt::Key_8, QStringLiteral("8")}},
    {KEY_9, {Qt::Key_9, QStringLiteral("9")}},

    {KEY_F1, {Qt::Key_F1, QStringLiteral("")}},
    {KEY_F2, {Qt::Key_F2, QStringLiteral("")}},
    {KEY_F3, {Qt::Key_F3, QStringLiteral("")}},
    {KEY_F4, {Qt::Key_F4, QStringLiteral("")}},
    {KEY_F5, {Qt::Key_F5, QStringLiteral("")}},
    {KEY_F6, {Qt::Key_F6, QStringLiteral("")}},
    {KEY_F7, {Qt::Key_F7, QStringLiteral("")}},
    {KEY_F8, {Qt::Key_F8, QStringLiteral("")}},
    {KEY_F9, {Qt::Key_F9, QStringLiteral("")}},
    {KEY_F10, {Qt::Key_F10, QStringLiteral("")}},
    {KEY_F11, {Qt::Key_F11, QStringLiteral("")}},
    {KEY_F12, {Qt::Key_F12, QStringLiteral("")}},
    {KEY_F13, {Qt::Key_F13, QStringLiteral("")}},
    {KEY_F14, {Qt::Key_F14, QStringLiteral("")}},
    {KEY_F15, {Qt::Key_F15, QStringLiteral("")}},
    {KEY_F16, {Qt::Key_F16, QStringLiteral("")}},
    {KEY_F17, {Qt::Key_F17, QStringLiteral("")}},
    {KEY_F18, {Qt::Key_F18, QStringLiteral("")}},

    // short press of the front panel standby button
    {KEY_F20, {Qt::Key_F20, QStringLiteral("")}},

    // long press of the front panel standby button
    {KEY_F21, {Qt::Key_F21, QStringLiteral("")}},

    // long press of the standby button
    {KEY_F22, {Qt::Key_F22, QStringLiteral("")}},

    // audio descriptions (accessibility rcu)
    {KEY_F23, {Qt::Key_F23, QStringLiteral("")}},

    // subtitles (accessibility rcu)
    {KEY_F24, {Qt::Key_F24, QStringLiteral("")}},

    // guide (accessibility rcu)
    {KEY_EPG, {Qt::Key_Guide, QStringLiteral("")}},

    // accessibility (accessibility rcu)
    {KEY_KPEQUAL, {Qt::Key_Support, QStringLiteral("")}},

    // battery low
    {KEY_BATTERY, {Qt::Key_Battery, QStringLiteral("")}},

    // FFV microphone button
    {KEY_MICMUTE, {Qt::Key_MicMute, QStringLiteral("")}},

    // Settings (cog) button on PR-1 RCUs only
    {KEY_KPDOT, {Qt::Key_Settings, QStringLiteral("")}},

    // WPS button on US devices
    {KEY_WPS_BUTTON, {Qt::Key_F26, QStringLiteral("")}},

    // app partner buttons
    {KEY_KPLEFTPAREN, {Qt::Key_ParenLeft, QStringLiteral("")}},   // youtube
    {KEY_KPRIGHTPAREN, {Qt::Key_ParenRight, QStringLiteral("")}}, // netflix
    {KEY_FN_F1, {Qt::Key_Launch0, QStringLiteral("")}},           // disney+
    {KEY_FN_F2, {Qt::Key_Launch1, QStringLiteral("")}},           // prime video
    {KEY_FN_F3, {Qt::Key_Launch2, QStringLiteral("")}},           // peacock
    {KEY_FN_F4, {Qt::Key_Launch3, QStringLiteral("")}},           // kayo
    {KEY_FN_F5, {Qt::Key_Launch4, QStringLiteral("")}},           // binge
    {KEY_FN_F6, {Qt::Key_Launch5, QStringLiteral("")}},           // xumo
    {KEY_FN_F7, {Qt::Key_Launch6, QStringLiteral("")}},           // amc+
    {KEY_FN_F8, {Qt::Key_Launch7, QStringLiteral("")}},           // to be allocated
    {KEY_FN_F9, {Qt::Key_Launch8, QStringLiteral("")}},           // to be allocated
    {KEY_FN_F10, {Qt::Key_Launch9, QStringLiteral("")}},          // to be allocated
    {KEY_FN_F11, {Qt::Key_LaunchA, QStringLiteral("")}},          // to be allocated
    {KEY_FN_F12, {Qt::Key_LaunchB, QStringLiteral("")}},          // to be allocated
    {KEY_FN_1, {Qt::Key_LaunchC, QStringLiteral("")}},            // to be allocated
    {KEY_FN_2, {Qt::Key_LaunchD, QStringLiteral("")}},            // to be allocated
    {KEY_FN_D, {Qt::Key_LaunchE, QStringLiteral("")}},            // to be allocated
    {KEY_FN_E, {Qt::Key_LaunchF, QStringLiteral("")}},            // to be allocated

};

void QWaylandSkyQInput::sendNativeEvent(QWindow* window, const EthanNativeEvent& event)
{
    QByteArray nativeEvent(reinterpret_cast<const char*>(&event), sizeof(EthanNativeEvent));

    // give app a chance to filter native event before sending
    long result = 0;
    QAbstractEventDispatcher* dispatcher = QAbstractEventDispatcher::instance();
    if (!dispatcher ||
        !dispatcher->filterNativeEvent(QByteArrayLiteral("HamiltronNativeEvent"), nativeEvent.data(), &result))
    {

        // not filtered so send on the native event to the window
        if (window)
            QWindowSystemInterface::handleNativeEvent(window, nativeEvent, nullptr, nullptr);
        else
            qCDebug(QtWaylandClient::lcQpaWayland, "no active window to receive native key event (0x%x)", event.key);
    }
}

void QWaylandSkyQInput::skyq_input_key(uint32_t serial, uint32_t time, uint32_t device_id, int32_t key, uint32_t state)
{
    // qCDebug(QtWaylandClient::lcQpaWayland,
    //        "Input key event : %u, %u, 0x%08x, %d, %u",
    //        serial, time, device_id, key, state);

    const QEvent::Type qtType = (state & 0x1) ? QEvent::KeyPress : QEvent::KeyRelease;
    const Qt::KeyboardModifiers qtModifiers = (state & 2) ? Qt::MetaModifier : Qt::NoModifier;

    // get the current active window
    QWindow* focus = QGuiApplication::focusWindow();

    // send the standard Qt key codes
    int qtKey = Qt::Key_unknown;
    auto keyDetails = mKeyMap.find(key);
    if (keyDetails == mKeyMap.end())
    {
        QWindowSystemInterface::handleExtendedKeyEvent(
            focus, static_cast<ulong>(time), qtType, qtKey, qtModifiers, key, 0, 0
        );
    }
    else
    {
        qtKey = keyDetails->first;
        QWindowSystemInterface::handleExtendedKeyEvent(
            focus, static_cast<ulong>(time), qtType, qtKey, qtModifiers, key, 0, 0, keyDetails->second
        );
    }

    // send the hamiltron events - this is for legacy EPG, which uses the
    // details to match the key press with the actual RCU device
    sendNativeEvent(focus, EthanNativeEventKey(time, device_id, state, qtKey));
}

void QWaylandSkyQInput::skyq_input_touchpad(
    uint32_t serial, uint32_t time, uint32_t device_id, int32_t x, int32_t y, uint32_t state
)
{
    Q_UNUSED(serial);

    const Qt::MouseButtons mouseButtons = state ? Qt::LeftButton : Qt::NoButton;

    // get the current active window and send the touchpad event as a mouse event
    QWindow* focus = QGuiApplication::focusWindow();
    if (focus)
        QWindowSystemInterface::handleMouseEvent(focus, time, QPointF(x, y), QPointF(x, y), mouseButtons, 0);

    // also send as a native event
    sendNativeEvent(focus, EthanNativeEventTouchpad(time, device_id, state, x, y));
}

void QWaylandSkyQInput::skyq_input_slider(uint32_t serial, uint32_t time, uint32_t device_id, int32_t x, uint32_t state)
{
    Q_UNUSED(serial);

    const Qt::MouseButtons mouseButtons = state ? Qt::RightButton : Qt::NoButton;

    // get the current active window and send the slider event as a mouse event
    QWindow* focus = QGuiApplication::focusWindow();
    if (focus)
        QWindowSystemInterface::handleMouseEvent(focus, time, QPointF(x, 0), QPointF(x, 0), mouseButtons, 0);

    // also send as a native event
    sendNativeEvent(focus, EthanNativeEventSlider(time, device_id, state, x));
}
