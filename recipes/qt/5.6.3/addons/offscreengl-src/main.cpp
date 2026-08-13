/****************************************************************************
**
** Qt 5.6.3 offscreengl platform plugin — adapted from entos-xe/qpa-offscreengl.
** Uses OSMesa (Mesa off-screen software renderer) via dlopen. No X11, no EGL,
** no display connection required — suitable for headless CI environments.
**
****************************************************************************/

#include "OffscreenGlIntegration.h"

#include <QDebug>
#include <qpa/qplatformintegrationplugin.h>

QT_BEGIN_NAMESPACE

class OffscreenGlIntegrationPlugin : public QPlatformIntegrationPlugin
{
    Q_OBJECT
    Q_PLUGIN_METADATA(IID QPlatformIntegrationFactoryInterface_iid FILE "offscreengl.json")
public:
    QPlatformIntegration *create(const QString &, const QStringList &) Q_DECL_OVERRIDE;
};

QPlatformIntegration *OffscreenGlIntegrationPlugin::create(const QString &system, const QStringList &paramList)
{
    if (!system.compare(QLatin1String("offscreengl"), Qt::CaseInsensitive))
        return new OffscreenGlIntegration(paramList);
    return nullptr;
}

QT_END_NAMESPACE

#include "main.moc"
