#include "qt563logging.h"
/****************************************************************************
**
** Copyright © 2019 Sky UK.
**
****************************************************************************/

#include "qwaylandnullinputdevice.h"
#include "qwaylandskyqinput.h"
#include "qwaylandskyqinputdeviceintegration_p.h"

#include <QtWaylandClient/private/qwaylanddisplay_p.h>

namespace QtWaylandClient
{

QWaylandSkyQInputDeviceIntegration::QWaylandSkyQInputDeviceIntegration() {}

void QWaylandSkyQInputDeviceIntegration::handleRegistryGlobal(
    void* data, ::wl_registry* registry, uint32_t id, const QString& interface, uint32_t version
)
{
    QWaylandSkyQInput* extension = static_cast<QWaylandSkyQInput*>(data);
    if (interface == QLatin1String("skyq_input") && !extension->isInitialized())
    {
        extension->init(registry, id, version);
    }
}

QWaylandInputDevice* QWaylandSkyQInputDeviceIntegration::createInputDevice(QWaylandDisplay* d, int version, uint32_t id)
{
    Q_UNUSED(version);
    Q_UNUSED(id);

    if (!m_skyqInput)
    {
        m_skyqInput.reset(new QWaylandSkyQInput);
        d->addRegistryListener(&QWaylandSkyQInputDeviceIntegration::handleRegistryGlobal, m_skyqInput.data());
    }

    return new QWaylandNullInputDevice(d, version, id);
}

} // namespace QtWaylandClient
