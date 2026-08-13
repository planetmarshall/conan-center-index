/****************************************************************************
**
** Copyright © 2019 Sky UK.
**
****************************************************************************/

#ifndef QWAYLANDWLSIMPLESHELLINTEGRATION_P_H
#define QWAYLANDWLSIMPLESHELLINTEGRATION_P_H

//
//  W A R N I N G
//  -------------
//
// This file is not part of the Qt API.  It exists purely as an
// implementation detail.  This header file may change from version to
// version without notice, or even be removed.
//
// We mean it.
//

#include <private/qwayland-wayland.h>
#include <QAbstractNativeEventFilter>
#include <QObject>
#include <QScopedPointer>
#include <QtWaylandClient/private/qwaylandshellintegration_p.h>
#include <wayland-client.h>

QT_BEGIN_NAMESPACE

namespace QtWaylandClient
{

class QWaylandWlSimpleShell;
class QWaylandSkyQShell;

class Q_WAYLAND_CLIENT_EXPORT QWaylandWlSimpleShellIntegration final : public QWaylandShellIntegration
{
public:
    QWaylandWlSimpleShellIntegration() = default;

    bool initialize(QWaylandDisplay*) override;
    QWaylandShellSurface* createShellSurface(QWaylandWindow* window) override;

private:
    QWaylandWlSimpleShell* m_wlSimpleShell = nullptr;
    QWaylandSkyQShell* m_skyQShell = nullptr;
};

} // namespace QtWaylandClient

QT_END_NAMESPACE

#endif // QWAYLANDWLSIMPLESHELLINTEGRATION_P_H
