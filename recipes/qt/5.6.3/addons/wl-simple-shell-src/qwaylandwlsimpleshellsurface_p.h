/****************************************************************************
**
** Copyright © 2019 Sky UK.
**
****************************************************************************/

#ifndef QWAYLANDWLSIMPLESHELLSURFACE_H
#define QWAYLANDWLSIMPLESHELLSURFACE_H

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

#include <QObject>
#include <QtCore/QRect>
#include <QtCore/QSize>
#include <QtWaylandClient/private/qwayland-wayland.h>
#include <QtWaylandClient/private/qwaylandshellsurface_p.h>
#include <QtWaylandClient/qtwaylandclientglobal.h>
#include <wayland-client.h>

QT_BEGIN_NAMESPACE

class QWindow;

namespace QtWaylandClient
{

class QWaylandWindow;
class QWaylandInputDevice;

class QWaylandWlSimpleShell;
class QWaylandSkyQShell;

class Q_WAYLAND_CLIENT_EXPORT QWaylandWlSimpleShellSurface : public QWaylandShellSurface
{
    Q_OBJECT
public:
    QWaylandWlSimpleShellSurface(
        QWaylandWindow* window, int surfaceId, QWaylandWlSimpleShell* shell, QWaylandSkyQShell* skyqShell
    );
    ~QWaylandWlSimpleShellSurface() override;

    void setSurfaceId(int surfaceId);
    int surfaceId() const;

    void setTitle(const QString& title) override;
    void setAppId(const QString& appId) override;

    void setWindowFlags(Qt::WindowFlags flags) override;
    void sendProperty(const QString& name, const QVariant& value) override;

protected:
    Q_SLOT void applyActive();

private:
    void syncVisibility();

    QWaylandWlSimpleShell* m_shell = nullptr;
    QWaylandSkyQShell* m_skyqShell = nullptr;
    QWaylandWindow* m_window = nullptr;
    int m_surfaceId;

    Qt::WindowFlags m_windowType;
    uint m_flags;

    QString m_title;
    bool m_visible;
    double m_opacity;
    QRect m_geometry;

    Qt::WindowStates m_ackedStates;
    Qt::WindowStates m_pendingStates;

    friend class QWaylandWindow;
};

QT_END_NAMESPACE

} // namespace QtWaylandClient

#endif // QWAYLANDWLSIMPLESHELLSURFACE_H
