/****************************************************************************
**
** Qt 5.6.3 offscreengl platform plugin — adapted from entos-xe/qpa-offscreengl.
**
****************************************************************************/

#ifndef OFFSCREENGLWINDOW_H
#define OFFSCREENGLWINDOW_H

#include <qpa/qplatformwindow.h>

QT_BEGIN_NAMESPACE

class OffscreenGlWindow : public QPlatformWindow
{
    friend class OffscreenGlContext;

public:
    OffscreenGlWindow(QWindow *wnd, void *libHandle);

    void setGeometry(const QRect &rect) Q_DECL_OVERRIDE;

private:
    void *m_libHandle;
};

QT_END_NAMESPACE

#endif // OFFSCREENGLWINDOW_H
