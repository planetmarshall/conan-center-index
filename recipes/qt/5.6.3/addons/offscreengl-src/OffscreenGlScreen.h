/****************************************************************************
**
** Qt 5.6.3 offscreengl platform plugin — adapted from entos-xe/qpa-offscreengl.
**
****************************************************************************/

#ifndef OFFSCREENGLSCREEN_H
#define OFFSCREENGLSCREEN_H

#include <qpa/qplatformintegration.h>
#include <qpa/qplatformscreen.h>

QT_BEGIN_NAMESPACE

class OffscreenGlScreen : public QPlatformScreen
{
public:
    OffscreenGlScreen();

    QRect geometry() const Q_DECL_OVERRIDE { return mGeometry; }
    int depth() const Q_DECL_OVERRIDE { return mDepth; }
    QImage::Format format() const Q_DECL_OVERRIDE { return mFormat; }

public:
    QRect mGeometry;
    int mDepth;
    QImage::Format mFormat;
};

QT_END_NAMESPACE

#endif // OFFSCREENGLSCREEN_H
