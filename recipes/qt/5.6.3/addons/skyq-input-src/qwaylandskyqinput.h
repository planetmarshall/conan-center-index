/****************************************************************************
**
** Copyright © 2019 Sky UK.
**
****************************************************************************/

#include <QMap>
#include <QObject>

#include "qwayland-skyq-input.h"

struct EthanNativeEvent;

QT_BEGIN_NAMESPACE

class QWindow;

class QWaylandSkyQInput final : public QObject, public QtWayland::skyq_input
{
    Q_OBJECT

public:
    QWaylandSkyQInput() = default;
    ~QWaylandSkyQInput() final = default;

private:
    void skyq_input_key(uint32_t serial, uint32_t time, uint32_t device_id, int32_t key, uint32_t state) override;
    void skyq_input_touchpad(
        uint32_t serial, uint32_t time, uint32_t device_id, int32_t x, int32_t y, uint32_t state
    ) override;
    void skyq_input_slider(uint32_t serial, uint32_t time, uint32_t device_id, int32_t x, uint32_t state) override;

private:
    void sendNativeEvent(QWindow* window, const EthanNativeEvent& event);

private:
    static const QMap<int32_t, std::pair<int, QString>> mKeyMap;
};

QT_END_NAMESPACE
