/****************************************************************************
**
** Qt 5.6.3 offscreengl platform plugin — adapted from entos-xe/qpa-offscreengl.
**
****************************************************************************/

#ifndef OFFSCREENGLBACKINGSTORE_H
#define OFFSCREENGLBACKINGSTORE_H

#include <qpa/qplatformbackingstore.h>
#include <qpa/qplatformwindow.h>
#include <QtGui/QImage>

QT_BEGIN_NAMESPACE

class OffscreenGlBackingStore : public QPlatformBackingStore
{
public:
    explicit OffscreenGlBackingStore(QWindow *window);
    ~OffscreenGlBackingStore() Q_DECL_OVERRIDE;

    QPaintDevice *paintDevice() Q_DECL_OVERRIDE;
    void flush(QWindow *window, const QRegion &region, const QPoint &offset) Q_DECL_OVERRIDE;
    void resize(const QSize &size, const QRegion &staticContents) Q_DECL_OVERRIDE;

private:
    QImage mImage;
    bool mDebug;
};

QT_END_NAMESPACE

#endif // OFFSCREENGLBACKINGSTORE_H
