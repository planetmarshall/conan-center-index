#include "qt563logging.h"
/****************************************************************************
**
** Copyright © 2019 Sky UK.
**
****************************************************************************/

#include "qwaylandskyqshell_p.h"
#include "qwaylandwlsimpleshell_p.h"
#include "qwaylandwlsimpleshellsurface_p.h"

#include <QtCore/QDebug>
#include <QtWaylandClient/private/qwaylandabstractdecoration_p.h>
#include <QtWaylandClient/private/qwaylanddisplay_p.h>
#include <QtWaylandClient/private/qwaylandextendedsurface_p.h>
#include <QtWaylandClient/private/qwaylandinputdevice_p.h>
#include <QtWaylandClient/private/qwaylandscreen_p.h>
#include <QtWaylandClient/private/qwaylandwindow_p.h>

QT_BEGIN_NAMESPACE

namespace QtWaylandClient
{

QWaylandWlSimpleShellSurface::QWaylandWlSimpleShellSurface(
    QWaylandWindow* window, int surfaceId, QWaylandWlSimpleShell* shell, QWaylandSkyQShell* skyqShell
)
    : QWaylandShellSurface(window)
    , m_shell(shell)
    , m_skyqShell(skyqShell)
    , m_window(window)
    , m_surfaceId(-1)
    , m_windowType(window->window()->type())
    , m_flags(0)
    , m_visible(false)
    , m_opacity(1.0f)
    , m_ackedStates(Qt::WindowNoState)
    , m_pendingStates(Qt::WindowNoState)
{

    // set the flags based on the window type
    if (m_windowType == Qt::WindowType::Popup)
    {
        window->window()->setFlags(window->window()->flags() | Qt::WindowTransparentForInput);
        m_flags |= SKYQ_SHELL_SKYQ_SURFACE_FLAGS_OVERLAY;
    }
    else if (m_windowType == Qt::WindowType::Dialog)
    {
        m_flags |= SKYQ_SHELL_SKYQ_SURFACE_FLAGS_OVERLAY;
    }

    qCDebug(lcQpaWayland) << this << ":created shell surface with type" << m_windowType;

    if (window->window()->flags() & Qt::WindowTransparentForInput)
        m_flags |= SKYQ_SHELL_SKYQ_SURFACE_FLAGS_TRANSPARENT_FOR_INPUT;

    // The skyq compositor defaults all surfaces to HIDDEN_BY_DEFAULT (which we
    // rely on so that OVERLAY flags can be applied before any buffer is
    // committed - the compositor refuses to toggle OVERLAY on a visible
    // surface).  Under that policy the plugin must explicitly tell the
    // compositor when Qt considers the window visible, otherwise the surface
    // stays hidden forever and the user sees a black screen.
    //
    // Qt 5.6.3's QWaylandShellSurface has no virtual setVisible() hook and
    // QWaylandWindow::setVisible() does not call into the shell surface, so
    // the only reliable way to observe show/hide transitions is via the
    // QWindow::visibleChanged signal.  Connect it here so any later show() or
    // hide() on the QWindow is forwarded to the compositor as set_visible.
    QObject::connect(window->window(), &QWindow::visibleChanged, this, &QWaylandWlSimpleShellSurface::syncVisibility);

    // check if a surfaceId has already been assigned
    if (surfaceId >= 0)
    {
        setSurfaceId(surfaceId);
    }
}

void QWaylandWlSimpleShellSurface::syncVisibility()
{
    if (!m_shell || m_surfaceId < 0)
        return;

    const bool visible = m_window->window()->isVisible();
    if (visible == m_visible)
        return;

    qCDebug(lcQpaWayland) << this << ":syncVisibility surface" << m_surfaceId << "->"
                          << (visible ? "visible" : "hidden");

    m_visible = visible;
    m_shell->set_visible(m_surfaceId, m_visible ? 1 : 0);
}

QWaylandWlSimpleShellSurface::~QWaylandWlSimpleShellSurface()
{
    qCDebug(lcQpaWayland) << this << ":destroying shell surface for surface id" << m_surfaceId;

    if (m_ackedStates & Qt::WindowActive)
    {
        window()->display()->handleWindowDeactivated(m_window);
        qCDebug(lcQpaWayland) << this << ": deactivated window / surface id" << m_surfaceId;
    }

    qCDebug(lcQpaWayland) << this << ": destructed" << m_surfaceId;
}

int QWaylandWlSimpleShellSurface::surfaceId() const
{
    return m_surfaceId;
}

void QWaylandWlSimpleShellSurface::setSurfaceId(int surfaceId)
{
    qCDebug(lcQpaWayland) << this << ":setSurfaceId" << surfaceId;

    // sanity check we haven't already set the surface id
    if (m_surfaceId == surfaceId)
    {
        qCWarning(lcQpaWayland) << "Already set surface id, ignoring second set event.";
        return;
    }
    if (m_surfaceId >= 0)
    {
        qCWarning(lcQpaWayland) << "Surface id has already been set to a different value.";
        return;
    }

    // assign the surface id
    m_surfaceId = surfaceId;

    // set the flags on the surface if non-standard (ie. popup or notification)
    if (m_skyqShell)
    {

        if (m_flags != 0)
        {
            qCDebug(lcQpaWayland) << "setting surface" << m_surfaceId << "flags to" << m_flags;
            m_skyqShell->set_surface_flags(m_surfaceId, m_flags);
        }
    }
    else
    {
        qCWarning(lcQpaWayland) << "missing m_skyqShell pointer";
    }

    // set the details of the surface if they've set by clients
    if (m_shell)
    {

        if (!m_title.isEmpty())
            m_shell->set_name(m_surfaceId, m_title);
        if (m_opacity != 1.0f)
            m_shell->set_opacity(m_surfaceId, wl_fixed_from_double(m_opacity));

        // The compositor defaults surfaces to HIDDEN_BY_DEFAULT so that we can
        // safely set OVERLAY before any buffer is committed.  That means we
        // must explicitly tell the compositor the surface is visible now; if
        // we don't the screen stays black.  By the time a surface id has
        // been assigned QWaylandWindow has finished initWindow(), which is
        // only entered for windows that are being shown, so it is always
        // correct to mark the surface visible here.  Any later hide/show
        // transitions are tracked via the QWindow::visibleChanged signal
        // wired up in the constructor.
        qCDebug(lcQpaWayland) << this << ":setSurfaceId sending set_visible(1)"
                              << "for surface" << m_surfaceId;
        m_visible = true;
        m_shell->set_visible(m_surfaceId, 1);

        // set the geometry of the surface if changed
        const QRect geometry = m_window->window()->frameGeometry();
        if (geometry != m_geometry)
        {
            m_geometry = geometry;
            m_shell->set_geometry(m_surfaceId, m_geometry.x(), m_geometry.y(), m_geometry.width(), m_geometry.height());
        }
    }
    else
    {
        qCWarning(lcQpaWayland) << "missing m_shell pointer";
    }

    // indicate the window is active, this also sets the focused window which
    // means all key events will now go to this window.  This is not really how
    // it's supposed to work, but good enough for now as all apps only have one
    // window
    if (!(m_flags & SKYQ_SHELL_SKYQ_SURFACE_FLAGS_TRANSPARENT_FOR_INPUT))
    {
        qCDebug(lcQpaWayland) << this << ":setSurfaceId - activating window";

        m_pendingStates |= Qt::WindowActive;

        QMetaObject::invokeMethod(this, "applyActive", Qt::QueuedConnection);
    }
}

void QWaylandWlSimpleShellSurface::applyActive()
{
    qCDebug(lcQpaWayland) << this << ":applyActive";

    if ((m_pendingStates & Qt::WindowActive) && !(m_ackedStates & Qt::WindowActive))
    {
        qCDebug(lcQpaWayland) << this << ":applyActive setting activated";
        m_window->display()->handleWindowActivated(m_window);
        m_ackedStates |= Qt::WindowActive;
    }

    if (!(m_pendingStates & Qt::WindowActive) && (m_ackedStates & Qt::WindowActive))
    {
        qCDebug(lcQpaWayland) << this << ":applyActive setting deactivated";
        m_window->display()->handleWindowDeactivated(m_window);
        m_ackedStates &= ~Qt::WindowActive;
    }
}

void QWaylandWlSimpleShellSurface::setTitle(const QString& title)
{
    qCDebug(lcQpaWayland) << this << ":setTitle" << title;

    m_title = title;

    if ((m_surfaceId >= 0) && m_shell)
        m_shell->set_name(m_surfaceId, title);
}

void QWaylandWlSimpleShellSurface::setAppId(const QString& appId)
{
    qCDebug(lcQpaWayland) << this << ":setAppId" << appId;
}

void QWaylandWlSimpleShellSurface::setWindowFlags(Qt::WindowFlags flags)
{
    qCDebug(lcQpaWayland) << this << ":setWindowFlags" << flags;

    uint newFlags = 0;

    const Qt::WindowFlags windowType = flags & Qt::WindowType_Mask;
    if (m_windowType != windowType)
    {
        qCWarning(lcQpaWayland) << "cannot change window type after creation";
    }

    if ((m_windowType == Qt::WindowType::Popup) || (m_windowType == Qt::WindowType::Dialog))
    {
        newFlags |= SKYQ_SHELL_SKYQ_SURFACE_FLAGS_OVERLAY;
    }

    if (flags & Qt::WindowTransparentForInput)
        newFlags |= SKYQ_SHELL_SKYQ_SURFACE_FLAGS_TRANSPARENT_FOR_INPUT;

    // if the 'WindowTransparentForInput' flag is changed, and the surface is
    // a popup surface, then we may need to activate or de-active the window
    if (((newFlags ^ m_flags) & SKYQ_SHELL_SKYQ_SURFACE_FLAGS_TRANSPARENT_FOR_INPUT) &&
        (newFlags & SKYQ_SHELL_SKYQ_SURFACE_FLAGS_OVERLAY))
    {

        if (newFlags & SKYQ_SHELL_SKYQ_SURFACE_FLAGS_TRANSPARENT_FOR_INPUT)
        {
            if (m_ackedStates & Qt::WindowActive)
                m_pendingStates &= ~Qt::WindowActive;
        }
        else
        {
            if (!(m_ackedStates & Qt::WindowActive))
                m_pendingStates |= Qt::WindowActive;
        }
    }

    if (newFlags != m_flags)
    {
        // Per skyshell protocol the OVERLAY flag can only be set / cleared
        // while the surface is not visible, and surface flags in general
        // cannot be changed once a buffer has been drawn.  Toggling OVERLAY
        // after the surface is up triggers a fatal Wayland protocol error
        // (the client gets disconnected and abort()s).  Warn and drop the
        // change in that case rather than crashing the app.
        const uint changedFlags = newFlags ^ m_flags;
        if ((changedFlags & SKYQ_SHELL_SKYQ_SURFACE_FLAGS_OVERLAY) && m_visible)
        {
            qCWarning(lcQpaWayland) << this << ": refusing to toggle OVERLAY flag on a visible surface;"
                                    << "current=" << m_flags << "requested=" << newFlags;
            return;
        }

        m_flags = newFlags;

        if ((m_surfaceId >= 0) && m_skyqShell)
        {
            qCDebug(lcQpaWayland) << "setting surface" << m_surfaceId << "flags to" << m_flags;
            m_skyqShell->set_surface_flags(m_surfaceId, m_flags);
        }
    }
}

void QWaylandWlSimpleShellSurface::sendProperty(const QString& name, const QVariant& value)
{
    qCDebug(lcQpaWayland) << this << ":sendProperty" << name << "=" << value;

    if (name.compare("surfaceOpacity", Qt::CaseInsensitive) == 0)
    {
        if (!value.canConvert<double>())
        {
            qCWarning(lcQpaWayland) << "Invalid variant value for 'surfaceOpacity' property.";
            return;
        }

        m_opacity = value.value<double>();

        if ((m_surfaceId >= 0) && m_shell)
            m_shell->set_opacity(m_surfaceId, wl_fixed_from_double(m_opacity));
    }
}

} // namespace QtWaylandClient

QT_END_NAMESPACE
