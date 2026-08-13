/****************************************************************************
**
** Qt 5.6.3 offscreengl platform plugin — adapted from entos-xe/qpa-offscreengl.
**
****************************************************************************/

#include "OffscreenGlIntegration.h"

#include "OffscreenGlBackingstore.h"
#include "OffscreenGlContext.h"
#include "OffscreenGlScreen.h"
#include "OffscreenGlWindow.h"

#include <dlfcn.h>
#include <qpa/qplatformwindow.h>
#include <qpa/qplatformfontdatabase.h>
#include <QtPlatformSupport/private/qgenericunixfontdatabase_p.h>
#include <QtPlatformSupport/private/qgenericunixeventdispatcher_p.h>
#include <QtGui/private/qguiapplication_p.h>
#include <QtGui/private/qpixmap_raster_p.h>

QT_BEGIN_NAMESPACE

static const char debugBackingStoreEnvironmentVariable[] = "QT_DEBUG_BACKINGSTORE";

static inline unsigned parseOptions(const QStringList &paramList)
{
    unsigned options = 0;
    for (const QString &param : paramList) {
        if (param == QLatin1String("enable_fonts"))
            options |= OffscreenGlIntegration::EnableFonts;
        else if (param == QLatin1String("fontconfig"))
            options |= OffscreenGlIntegration::FontconfigDatabase;
    }
    return options;
}

OffscreenGlIntegration::OffscreenGlIntegration(const QStringList &parameters)
    : m_fontDatabase(nullptr)
    , m_primaryScreen(new OffscreenGlScreen())
    , m_options(parseOptions(parameters))
    , m_handle(nullptr)
{
    if (qEnvironmentVariableIsSet(debugBackingStoreEnvironmentVariable) &&
        qEnvironmentVariableIntValue(debugBackingStoreEnvironmentVariable) > 0) {
        m_options |= DebugBackingStore | EnableFonts;
    }

    m_primaryScreen->mGeometry = QRect(0, 0, 1920, 1080);
    m_primaryScreen->mDepth = 32;
    m_primaryScreen->mFormat = QImage::Format_ARGB32_Premultiplied;

    screenAdded(m_primaryScreen);

    m_handle = dlopen("libOSMesa.so", RTLD_NOW | RTLD_LOCAL);
    if (!m_handle)
        m_handle = dlopen("libOSMesa.so.8", RTLD_NOW | RTLD_LOCAL);
    if (!m_handle)
        m_handle = dlopen("libOSMesa.so.6", RTLD_NOW | RTLD_LOCAL);
    if (!m_handle)
        qFatal("offscreengl: unable to open libOSMesa.so. Install: sudo apt install libosmesa6");
}

OffscreenGlIntegration::~OffscreenGlIntegration()
{
    destroyScreen(m_primaryScreen);
    delete m_fontDatabase;
}

bool OffscreenGlIntegration::hasCapability(QPlatformIntegration::Capability cap) const
{
    switch (cap) {
    case ThreadedPixmaps:
    case MultipleWindows:
    case OpenGL:
    case ThreadedOpenGL:
    case SharedGraphicsCache:
    case AllGLFunctionsQueryable: // ensures QOpenGLFunctions resolves GL 1.x via getProcAddress
        return true;
    default:
        return QPlatformIntegration::hasCapability(cap);
    }
}

// Dummy font database — does not scan the font directory.
// Used when EnableFonts is not set (the default for component tests).
class DummyFontDatabase : public QPlatformFontDatabase
{
public:
    void populateFontDatabase() Q_DECL_OVERRIDE {}
};

QPlatformFontDatabase *OffscreenGlIntegration::fontDatabase() const
{
    if (!m_fontDatabase) {
        if (m_options & EnableFonts)
            m_fontDatabase = new QGenericUnixFontDatabase();
        else
            m_fontDatabase = new DummyFontDatabase();
    }
    return m_fontDatabase;
}

QPlatformWindow *OffscreenGlIntegration::createPlatformWindow(QWindow *window) const
{
    QPlatformWindow *w = new OffscreenGlWindow(window, m_handle);
    w->requestActivateWindow();
    return w;
}

QPlatformBackingStore *OffscreenGlIntegration::createPlatformBackingStore(QWindow *window) const
{
    return new OffscreenGlBackingStore(window);
}

QAbstractEventDispatcher *OffscreenGlIntegration::createEventDispatcher() const
{
    return createUnixEventDispatcher();
}

QPlatformOpenGLContext *OffscreenGlIntegration::createPlatformOpenGLContext(QOpenGLContext *context) const
{
    return new OffscreenGlContext(m_handle, context);
}

OffscreenGlIntegration *OffscreenGlIntegration::instance()
{
    return static_cast<OffscreenGlIntegration *>(QGuiApplicationPrivate::platformIntegration());
}

QT_END_NAMESPACE
