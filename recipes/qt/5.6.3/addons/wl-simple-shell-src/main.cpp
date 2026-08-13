#include "qt563logging.h"
/****************************************************************************
**
** Copyright © 2019 Sky UK.
**
****************************************************************************/

#include "qwaylandwlsimpleshellintegration_p.h"

#include <QObject>
#include <QtWaylandClient/private/qwaylandshellintegrationplugin_p.h>

QT_BEGIN_NAMESPACE

namespace QtWaylandClient
{
Q_LOGGING_CATEGORY(lcQpaWayland, "qt.qpa.wayland")

class QWaylandWlSimpleShellIntegrationPlugin : public QWaylandShellIntegrationPlugin
{
    Q_OBJECT
    Q_PLUGIN_METADATA(IID QWaylandShellIntegrationFactoryInterface_iid FILE "wl-simple-shell.json")

public:
    QWaylandShellIntegration* create(const QString& key, const QStringList& paramList) override;
};

QWaylandShellIntegration*
QWaylandWlSimpleShellIntegrationPlugin::create(const QString& key, const QStringList& paramList)
{
    Q_UNUSED(key);
    Q_UNUSED(paramList);
    return new QWaylandWlSimpleShellIntegration();
}

} // namespace QtWaylandClient

QT_END_NAMESPACE

#include "main.moc"
