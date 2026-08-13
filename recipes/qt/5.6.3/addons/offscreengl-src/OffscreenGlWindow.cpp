/****************************************************************************
**
** Qt 5.6.3 offscreengl platform plugin — adapted from entos-xe/qpa-offscreengl.
**
****************************************************************************/

#include "OffscreenGlWindow.h"

QT_BEGIN_NAMESPACE

OffscreenGlWindow::OffscreenGlWindow(QWindow *wnd, void *libHandle)
    : QPlatformWindow(wnd)
    , m_libHandle(libHandle)
{
}

void OffscreenGlWindow::setGeometry(const QRect &rect)
{
    QPlatformWindow::setGeometry(rect);
}

QT_END_NAMESPACE
