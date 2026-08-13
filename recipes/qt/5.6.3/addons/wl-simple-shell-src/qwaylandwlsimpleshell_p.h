/****************************************************************************
**
** Copyright © 2019 Sky UK.
****************************************************************************/

#ifndef QWAYLANDWLSIMPLESHELL_P_H
#define QWAYLANDWLSIMPLESHELL_P_H

#include <private/qwayland-wayland.h>
#include <QObject>
#include <QtCore/QMap>
#include <QtCore/QMutex>
#include <wayland-client.h>

#include "qwayland-simple-shell.h"

QT_BEGIN_NAMESPACE

namespace QtWaylandClient
{

class QWaylandDisplay;

class QWaylandWlSimpleShell final : public QtWayland::wl_simple_shell
{
public:
    QWaylandWlSimpleShell(QWaylandDisplay* display, int id, int version);
    ~QWaylandWlSimpleShell() final = default;

public:
    int takeSurfaceId(::wl_surface* surface);

protected:
    void simple_shell_surface_id(struct ::wl_surface* surface, uint32_t surfaceId) override;
    void simple_shell_surface_created(uint32_t surfaceId, const QString& name) override;
    void simple_shell_surface_destroyed(uint32_t surfaceId, const QString& name) override;
    void simple_shell_surface_status(
        uint32_t surfaceId,
        const QString& name,
        uint32_t visible,
        int32_t x,
        int32_t y,
        int32_t width,
        int32_t height,
        wl_fixed_t opacity,
        wl_fixed_t zorder
    ) override;
    void simple_shell_get_surfaces_done() override;

private:
    QWaylandDisplay* m_display;
    QMutex m_surfaceIdsLock;
    QMap<::wl_surface*, uint32_t> m_surfaceIds;
};

} // namespace QtWaylandClient

QT_END_NAMESPACE

#endif // QWAYLANDWLSIMPLESHELL_P_H
