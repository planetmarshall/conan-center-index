#include "qt563logging.h"
/****************************************************************************
**
** Copyright © 2019 Sky UK.
**
****************************************************************************/

#include "qwaylandwlsimpleshell_p.h"
#include "qwaylandwlsimpleshellintegration_p.h"
#include "qwaylandwlsimpleshellsurface_p.h"

#include <QtWaylandClient/private/qwaylanddisplay_p.h>
#include <QtWaylandClient/private/qwaylandwindow_p.h>

QT_BEGIN_NAMESPACE

namespace QtWaylandClient
{

QWaylandWlSimpleShell::QWaylandWlSimpleShell(QWaylandDisplay* display, int id, int version)
    : QtWayland::wl_simple_shell(display->wl_registry(), id, version)
    , m_display(display)
{
}

void QWaylandWlSimpleShell::simple_shell_surface_id(struct ::wl_surface* surface, uint32_t surfaceId)
{
    // this is called after the surface is created to tell us the id that westeros
    // has assigned to the surface, we pass this on to the QWaylandSimpleShellSurface
    // object
    qCDebug(QtWaylandClient::lcQpaWayland, "wl_surface %p assigned id %u", surface, surfaceId);

    if (!surface)
        return;

    // check if already have a shell surface created for this wl_surface in which
    // case tell it its new surfaceId
    QWaylandWindow* window = QWaylandWindow::fromWlSurface(surface);
    if (window)
    {
        auto shellSurface = reinterpret_cast<QWaylandWlSimpleShellSurface*>(window->shellSurface());
        if (shellSurface)
        {
            shellSurface->setSurfaceId(static_cast<int>(surfaceId));
            return;
        }
    }

    // no window for the surface yet, so store until either takeSurfaceId
    // is called or we get a notification on the surface being destroyed
    QMutexLocker locker(&m_surfaceIdsLock);
    m_surfaceIds[surface] = surfaceId;
}

int QWaylandWlSimpleShell::takeSurfaceId(::wl_surface* surface)
{
    QMutexLocker locker(&m_surfaceIdsLock);

    if (m_surfaceIds.contains(surface))
    {
        qCDebug(QtWaylandClient::lcQpaWayland, "taking wl_surface %p mapping out of the map", surface);
        return static_cast<int>(m_surfaceIds.take(surface));
    }

    return -1;
}

void QWaylandWlSimpleShell::simple_shell_surface_created(uint32_t surfaceId, const QString& name)
{
    qCDebug(QtWaylandClient::lcQpaWayland, "surface %u name is '%s'", surfaceId, qPrintable(name));

    Q_UNUSED(surfaceId);
    Q_UNUSED(name);
}

void QWaylandWlSimpleShell::simple_shell_surface_destroyed(uint32_t surfaceId, const QString& name)
{
    qCDebug(QtWaylandClient::lcQpaWayland, "surface %u with name '%s' destroyed", surfaceId, qPrintable(name));

    Q_UNUSED(name);

    QMutexLocker locker(&m_surfaceIdsLock);

    // remove the surface from our internal map
    auto it = m_surfaceIds.begin();
    while (it != m_surfaceIds.end())
    {
        if (static_cast<uint32_t>(it.value()) == surfaceId)
            it = m_surfaceIds.erase(it);
        else
            ++it;
    }
}

void QWaylandWlSimpleShell::simple_shell_surface_status(
    uint32_t surfaceId,
    const QString& name,
    uint32_t visible,
    int32_t x,
    int32_t y,
    int32_t width,
    int32_t height,
    wl_fixed_t opacity,
    wl_fixed_t zorder
)
{
    qCDebug(QtWaylandClient::lcQpaWayland, "surface %u status '%s' ...", surfaceId, qPrintable(name));

    Q_UNUSED(surfaceId);
    Q_UNUSED(name);
    Q_UNUSED(visible);
    Q_UNUSED(x);
    Q_UNUSED(y);
    Q_UNUSED(width);
    Q_UNUSED(height);
    Q_UNUSED(opacity);
    Q_UNUSED(zorder);
}

void QWaylandWlSimpleShell::simple_shell_get_surfaces_done() {}

} // namespace QtWaylandClient

QT_END_NAMESPACE
