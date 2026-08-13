/**********************************************************************************************************************
 * (C)opyright BSkyB 2013 onwards
 * All rights reserved
 * This file is proprietary and confidential.
 * Do not disclose to third parties without explicit permission
 **********************************************************************************************************************/

#ifndef ETHANNATIVEEVENT_H
#define ETHANNATIVEEVENT_H

#include <QString>
#include <QtGlobal>

///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

#define ETHAN_NATIVE_KEY 0
#define ETHAN_NATIVE_TOUCHPAD 1
#define ETHAN_NATIVE_SLIDER 2

#define ETHAN_STATE_VIRTUAL 2U

#define ETHAN_STATE_UP 0U
#define ETHAN_STATE_DOWN 1U
#define ETHAN_STATE_VIRTUAL_UP (ETHAN_STATE_UP | ETHAN_STATE_VIRTUAL)
#define ETHAN_STATE_VIRTUAL_DOWN (ETHAN_STATE_DOWN | ETHAN_STATE_VIRTUAL)

struct EthanNativeEvent
{
    quint32 eventType;
    quint32 time;
    quint32 deviceId;
    quint32 state;
    union
    {
        quint32 x;
        quint32 key;
    };
    quint32 y;
};

struct EthanNativeEventKey : EthanNativeEvent
{
    // cppcheck-suppress uninitDerivedMemberVar
    EthanNativeEventKey(quint32 _time, quint32 _deviceId, quint32 _state, quint32 _key)
    {
        eventType = ETHAN_NATIVE_KEY;
        time = _time;
        deviceId = _deviceId;
        state = _state;
        key = _key;
        y = 0;
    }
};

struct EthanNativeEventTouchpad : EthanNativeEvent
{
    // cppcheck-suppress uninitDerivedMemberVar
    EthanNativeEventTouchpad(quint32 _time, quint32 _deviceId, quint32 _state, quint32 _x, quint32 _y)
    {
        eventType = ETHAN_NATIVE_TOUCHPAD;
        time = _time;
        deviceId = _deviceId;
        state = _state;
        x = _x;
        y = _y;
    }
};

struct EthanNativeEventSlider : EthanNativeEvent
{
    // cppcheck-suppress uninitDerivedMemberVar
    EthanNativeEventSlider(quint32 _time, quint32 _deviceId, quint32 _state, quint32 _x)
    {
        eventType = ETHAN_NATIVE_SLIDER;
        time = _time;
        deviceId = _deviceId;
        state = _state;
        x = _x;
        y = 0;
    }
};

#endif // ETHANNATIVEEVENT_H
