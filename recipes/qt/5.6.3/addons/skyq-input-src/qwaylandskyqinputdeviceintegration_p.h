/****************************************************************************
**
** Copyright © 2019 Sky UK.
**
****************************************************************************/

#ifndef QWAYLANDSKYRDKINPUTDEVICEINTEGRATION_H
#define QWAYLANDSKYRDKINPUTDEVICEINTEGRATION_H

#include <QObject>
#include <QScopedPointer>
#include <QtWaylandClient/private/qwaylandinputdeviceintegration_p.h>

struct wl_interface;
struct wl_registry;

QT_BEGIN_NAMESPACE

class QWaylandSkyQInput;

namespace QtWaylandClient
{

class QWaylandSkyQInputDeviceIntegration final : public QWaylandInputDeviceIntegration
{
public:
    QWaylandSkyQInputDeviceIntegration();
    ~QWaylandSkyQInputDeviceIntegration() final = default;

    QWaylandInputDevice* createInputDevice(QWaylandDisplay* d, int version, uint32_t id) override;

private:
    static void
    handleRegistryGlobal(void* data, ::wl_registry* registry, uint32_t id, const QString& interface, uint32_t version);

private:
    QScopedPointer<QWaylandSkyQInput> m_skyqInput;
};

} // namespace QtWaylandClient

QT_END_NAMESPACE

#endif // QWAYLANDSKYRDKINPUTDEVICEINTEGRATION_H
