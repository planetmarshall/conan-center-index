/****************************************************************************
**
** Copyright © 2019 Sky UK.
**
****************************************************************************/

#ifndef QWAYLANDSKYQSHELL_P_H
#define QWAYLANDSKYQSHELL_P_H

#include <private/qwayland-wayland.h>
#include <QObject>
#include <wayland-client.h>

#include "qwayland-skyq-shell.h"

QT_BEGIN_NAMESPACE

namespace QtWaylandClient
{

class QWaylandDisplay;

class QWaylandSkyQShell final : public QtWayland::skyq_shell
{
public:
    QWaylandSkyQShell(QWaylandDisplay* display, int id, int version);
    ~QWaylandSkyQShell() final = default;

private:
    void skyq_shell_state_changed(uint32_t state) override;
    void skyq_shell_close() override;
};

} // namespace QtWaylandClient

QT_END_NAMESPACE

#endif // QWAYLANDSKYQSHELL_P_H
