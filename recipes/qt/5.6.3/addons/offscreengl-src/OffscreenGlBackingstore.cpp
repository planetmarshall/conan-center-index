/****************************************************************************
**
** Qt 5.6.3 offscreengl platform plugin — adapted from entos-xe/qpa-offscreengl.
**
****************************************************************************/

#include "OffscreenGlBackingstore.h"

#include "OffscreenGlIntegration.h"

#include <private/qguiapplication_p.h>
#include <QGuiApplication>
#include <qpa/qplatformscreen.h>
#include <QScreen>
#include <QtCore/qdebug.h>

QT_BEGIN_NAMESPACE

OffscreenGlBackingStore::OffscreenGlBackingStore(QWindow* window)
    : QPlatformBackingStore(window)
    , mDebug(OffscreenGlIntegration::instance()->options() & OffscreenGlIntegration::DebugBackingStore)
{
}

OffscreenGlBackingStore::~OffscreenGlBackingStore() {}

QPaintDevice* OffscreenGlBackingStore::paintDevice()
{
    return &mImage;
}

void OffscreenGlBackingStore::flush(QWindow* window, const QRegion& region, const QPoint& offset)
{
    Q_UNUSED(window);
    Q_UNUSED(region);
    Q_UNUSED(offset);

    if (mDebug)
    {
        static int c = 0;
        QString filename = QString("output%1.png").arg(c++, 4, 10, QLatin1Char('0'));
        mImage.save(filename);
    }
}

void OffscreenGlBackingStore::resize(const QSize& size, const QRegion&)
{
    QImage::Format format = QGuiApplication::primaryScreen()->handle()->format();
    if (mImage.size() != size)
        mImage = QImage(size, format);
}

QT_END_NAMESPACE
