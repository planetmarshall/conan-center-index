#include "qt563logging.h"
/****************************************************************************
**
** Copyright © 2019 Sky UK.
**
****************************************************************************/

#include "qwaylandnullinputdevice.h"

namespace QtWaylandClient
{

QWaylandNullInputDevice::QWaylandNullInputDevice(QWaylandDisplay* display, int version, uint32_t id)
    : QWaylandInputDevice(display, version, id)
{
}

void QWaylandNullInputDevice::seat_capabilities(uint32_t caps)
{
    // we override this callback to disable all input devices for a given
    // wl_seat - we use this on the Sky QPA as we get input events via the
    // specific skyq_input interface
}

} // namespace QtWaylandClient
