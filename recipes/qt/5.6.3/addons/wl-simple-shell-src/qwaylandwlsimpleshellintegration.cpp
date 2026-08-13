#include "qt563logging.h"
/****************************************************************************
**
** Copyright © 2019 Sky UK.
**
****************************************************************************/

#include "qwaylandskyqshell_p.h"
#include "qwaylandwlsimpleshell_p.h"
#include "qwaylandwlsimpleshellintegration_p.h"
#include "qwaylandwlsimpleshellsurface_p.h"

#include <QtWaylandClient/private/qwaylanddisplay_p.h>
#include <QtWaylandClient/private/qwaylandwindow_p.h>

QT_BEGIN_NAMESPACE

namespace QtWaylandClient
{

bool QWaylandWlSimpleShellIntegration::initialize(QWaylandDisplay* display)
{
    Q_FOREACH (QWaylandDisplay::RegistryGlobal global, display->globals())
    {

        if (global.interface == QLatin1String("wl_simple_shell"))
        {
            m_wlSimpleShell = new QWaylandWlSimpleShell(display, global.id, 1);
        }

        if (global.interface == QLatin1String("skyq_shell"))
        {
            m_skyQShell = new QWaylandSkyQShell(display, global.id, 3);
        }
    }

    if (!m_wlSimpleShell)
    {
        qCWarning(lcQpaWayland) << "Couldn't find global wl_simple_shell interface";
        return false;
    }

    if (!m_skyQShell)
    {
        qCWarning(lcQpaWayland) << "Couldn't find global skyq_shell interface";
    }
    else
    {
        // the following tells the window manager that when surfaces are created
        // they're not created in the visible state
        QByteArray policy = qgetenv("SKYQ_SHELL_VISIBILITY_POLICY");
        if (policy.toUpper() == "VISIBLE")
            m_skyQShell->set_visibility_policy(SKYQ_SHELL_VISIBILITY_POLICY_VISIBLE_BY_DEFAULT);
        else
            m_skyQShell->set_visibility_policy(SKYQ_SHELL_VISIBILITY_POLICY_HIDDEN_BY_DEFAULT);
    }

    return true;
}

QWaylandShellSurface* QWaylandWlSimpleShellIntegration::createShellSurface(QWaylandWindow* window)
{
    qCDebug(lcQpaWayland, "creating shell surface");

    int surfaceId = m_wlSimpleShell->takeSurfaceId(window->object());
    return new QWaylandWlSimpleShellSurface(window, surfaceId, m_wlSimpleShell, m_skyQShell);
}

} // namespace QtWaylandClient

QT_END_NAMESPACE
