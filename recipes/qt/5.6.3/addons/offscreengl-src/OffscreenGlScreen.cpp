/****************************************************************************
**
** Qt 5.6.3 offscreengl platform plugin — adapted from entos-xe/qpa-offscreengl.
**
****************************************************************************/

#include "OffscreenGlScreen.h"

QT_BEGIN_NAMESPACE

OffscreenGlScreen::OffscreenGlScreen()
    : mGeometry(0, 0, 1920, 1080)
    , mDepth(32)
    , mFormat(QImage::Format_ARGB32_Premultiplied)
{
}

QT_END_NAMESPACE
