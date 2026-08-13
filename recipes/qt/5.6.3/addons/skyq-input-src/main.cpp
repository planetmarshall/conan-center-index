/****************************************************************************
**
** Copyright © 2019 Sky UK.
**
****************************************************************************/

#include "qwaylandskyqinputdeviceintegration_p.h"

#include <QObject>
#include <QtWaylandClient/private/qwaylandinputdeviceintegrationplugin_p.h>

QT_BEGIN_NAMESPACE

namespace QtWaylandClient
{

class QWaylandSkyQInputDeviceIntegrationPlugin : public QWaylandInputDeviceIntegrationPlugin
{
    Q_OBJECT
    Q_PLUGIN_METADATA(IID QWaylandInputDeviceIntegrationFactoryInterface_iid FILE "skyq-input.json")

public:
    QWaylandInputDeviceIntegration* create(const QString& key, const QStringList& paramList) override;
};

QWaylandInputDeviceIntegration*
QWaylandSkyQInputDeviceIntegrationPlugin::create(const QString& key, const QStringList& paramList)
{
    Q_UNUSED(key);
    Q_UNUSED(paramList);
    return new QWaylandSkyQInputDeviceIntegration();
}

} // namespace QtWaylandClient

QT_END_NAMESPACE

#include "main.moc"
