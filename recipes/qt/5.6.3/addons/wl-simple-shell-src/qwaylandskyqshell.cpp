#include "qt563logging.h"
/****************************************************************************
**
** Copyright © 2019 Sky UK.
**
****************************************************************************/

#include "qwaylandskyqshell_p.h"
#include "qwaylandwlsimpleshellintegration_p.h"
#include "qwaylandwlsimpleshellsurface_p.h"

#include <qguiapplication.h>
#include <qpa/qwindowsysteminterface.h>
#include <QtWaylandClient/private/qwaylanddisplay_p.h>
#include <QtWaylandClient/private/qwaylandwindow_p.h>

QT_BEGIN_NAMESPACE

namespace QtWaylandClient
{

QWaylandSkyQShell::QWaylandSkyQShell(QWaylandDisplay* display, int id, int version)
    : QtWayland::skyq_shell(display->wl_registry(), id, version)
{
}

void QWaylandSkyQShell::skyq_shell_state_changed(uint32_t state)
{
    switch (state)
    {
    case SKYQ_SHELL_STATE_ACTIVE:
        qCDebug(QtWaylandClient::lcQpaWayland) << "skyq_shell state change event -> active";
        QWindowSystemInterface::handleApplicationStateChanged(Qt::ApplicationActive);
        break;
    case SKYQ_SHELL_STATE_INACTIVE:
        qCDebug(QtWaylandClient::lcQpaWayland) << "skyq_shell state change event -> inactive";
        QWindowSystemInterface::handleApplicationStateChanged(Qt::ApplicationInactive);
        break;
    case SKYQ_SHELL_STATE_HIDDEN:
        qCDebug(QtWaylandClient::lcQpaWayland) << "skyq_shell state change event -> hidden";
        QWindowSystemInterface::handleApplicationStateChanged(Qt::ApplicationHidden);
        break;
    case SKYQ_SHELL_STATE_SUSPENDED:
        qCDebug(QtWaylandClient::lcQpaWayland) << "skyq_shell state change event -> suspended";
        QWindowSystemInterface::handleApplicationStateChanged(Qt::ApplicationSuspended);
        QWindowSystemInterface::flushWindowSystemEvents();
        break;

    default:
        qCWarning(QtWaylandClient::lcQpaWayland) << "unknown skyq_shell state value" << state;
        break;
    }
}

void QWaylandSkyQShell::skyq_shell_close()
{
    qCDebug(QtWaylandClient::lcQpaWayland) << "skyq_shell received app terminate request";

    QCloseEvent ev;
    QGuiApplication::sendEvent(qGuiApp, &ev);
    if (ev.isAccepted())
    {
        QGuiApplication::exit(0);
    }
}

} // namespace QtWaylandClient

QT_END_NAMESPACE
