/****************************************************************************
**
** Copyright © 2019 Sky UK.
**
****************************************************************************/

#ifndef QWAYLANDNULLINPUTDEVICE_H
#define QWAYLANDNULLINPUTDEVICE_H

#include <QObject>
#include <QtWaylandClient/private/qwaylandinputdevice_p.h>

QT_BEGIN_NAMESPACE

namespace QtWaylandClient
{

class QWaylandNullInputDevice : public QWaylandInputDevice
{
public:
    QWaylandNullInputDevice(QWaylandDisplay* display, int version, uint32_t id);
    ~QWaylandNullInputDevice() override = default;

private:
    void seat_capabilities(uint32_t caps) override;
};

} // namespace QtWaylandClient

QT_END_NAMESPACE

#endif // QWAYLANDNULLINPUTDEVICE_H
