/****************************************************************************
**
** Qt 5.6.3 offscreengl platform plugin — adapted from entos-xe/qpa-offscreengl.
**
****************************************************************************/

#include "OffscreenGlContext.h"
#include "OffscreenGlWindow.h"

#include <dlfcn.h>
#include <GL/osmesa.h>
#include <QDebug>
#include <QOpenGLContext>
#include <qpa/qplatformoffscreensurface.h>

QT_BEGIN_NAMESPACE

OffscreenGlContext::OffscreenGlContext(void *libHandle, QOpenGLContext *context)
    : m_osmesaCtx(nullptr)
    , m_libHandle(libHandle)
{
    // Qt 5.6.3: CTAD not available — use C array for attrib list
    const int attribList[] = {
        OSMESA_FORMAT,  OSMESA_BGRA,
        OSMESA_PROFILE, OSMESA_COMPAT_PROFILE,
        0
    };

    OSMesaCreateContextAttribs = (OSMesaCreateContextAttribsFn)dlsym(m_libHandle, "OSMesaCreateContextAttribs");
    OSMesaMakeCurrent          = (OSMesaMakeCurrentFn)dlsym(m_libHandle, "OSMesaMakeCurrent");
    OSMesaDestroyContext       = (OSMesaDestroyContextFn)dlsym(m_libHandle, "OSMesaDestroyContext");

    if (!OSMesaCreateContextAttribs || !OSMesaMakeCurrent || !OSMesaDestroyContext) {
        qFatal("offscreengl: failed to resolve OSMesa functions from libOSMesa");
        return;
    }

    // Resolve share context
    OSMesaContext share = nullptr;
    auto platContx = context->shareHandle();
    auto osglCtx = dynamic_cast<OffscreenGlContext *>(platContx);
    if (osglCtx) {
        share = osglCtx->m_osmesaCtx;
        m_hasShareContext = true;
    }

    m_osmesaCtx = OSMesaCreateContextAttribs(attribList, share);
    if (!m_osmesaCtx) {
        qCritical("offscreengl: unable to create GL context with OSMesa");
        return;
    }

    // Verify context works with a tiny dummy buffer
    uchar buffer[4];
    if (!OSMesaMakeCurrent(m_osmesaCtx, buffer, GL_UNSIGNED_BYTE, 1, 1))
        qCritical("offscreengl: OSMesaMakeCurrent failed on dummy buffer");
}

OffscreenGlContext::~OffscreenGlContext()
{
    if (m_osmesaCtx)
        OSMesaDestroyContext(m_osmesaCtx);
}

QSurfaceFormat OffscreenGlContext::format() const
{
    QSurfaceFormat fmt;
    fmt.setAlphaBufferSize(8);
    fmt.setBlueBufferSize(8);
    fmt.setDepthBufferSize(0);
    fmt.setGreenBufferSize(8);
    fmt.setRedBufferSize(8);
    fmt.setStencilBufferSize(0);
    fmt.setMajorVersion(3);
    fmt.setMinorVersion(2);
    return fmt;
}

void OffscreenGlContext::swapBuffers(QPlatformSurface *surface)
{
    Q_UNUSED(surface);
    // Ensure all pending GL commands are executed before the caller reads
    // the OSMesa buffer. OSMesa is synchronous but glFlush() is the contract.
    glFlush();
}

bool OffscreenGlContext::makeCurrent(QPlatformSurface *surface)
{
    if (!m_osmesaCtx)
        return false;

    auto *wnd = dynamic_cast<OffscreenGlWindow *>(surface);
    if (wnd)
    {
        // Window surface: render into the window's pixel buffer at its geometry.
        QRect geometry = wnd->geometry();
        constexpr int numChannels = 4;
        m_buffer.resize(static_cast<size_t>(geometry.width() * geometry.height() * numChannels));
        return OSMesaMakeCurrent(m_osmesaCtx, m_buffer.data(), GL_UNSIGNED_BYTE,
                                 geometry.width(), geometry.height());
    }

    // QPlatformOffscreenSurface: used by QtSharedOpenGLContext for worker threads
    // (e.g. TextureLoader). No rendering is done on this surface — the context only
    // needs to be current so GL operations (PBO upload, glFenceSync) can execute.
    // Use a tiny 1×1 buffer; the actual pixel output is irrelevant.
    if (dynamic_cast<QPlatformOffscreenSurface *>(surface))
    {
        if (m_buffer.size() < 4)
            m_buffer.resize(4);
        bool ok = OSMesaMakeCurrent(m_osmesaCtx, m_buffer.data(), GL_UNSIGNED_BYTE, 1, 1);
        qDebug("[DIAG] OffscreenGlContext::makeCurrent QPlatformOffscreenSurface ok=%d sharing=%d", ok, m_hasShareContext);
        return ok;
    }

    return false;
}

void OffscreenGlContext::doneCurrent()
{
}

bool OffscreenGlContext::isSharing() const
{
    // Report true when this context was created with a share context so that
    // Qt's share group tracking works correctly. This enables PBO/texture
    // sharing between the worker context (TextureLoader) and the main context.
    return m_hasShareContext;
}

bool OffscreenGlContext::isValid() const
{
    return m_osmesaCtx != nullptr;
}

// Qt 5.6.3: getProcAddress takes QByteArray, not const char*
QFunctionPointer OffscreenGlContext::getProcAddress(const QByteArray &procName)
{
    return reinterpret_cast<QFunctionPointer>(dlsym(m_libHandle, procName.constData()));
}

GLuint OffscreenGlContext::defaultFramebufferObject(QPlatformSurface *surface) const
{
    Q_UNUSED(surface);
    return 0;
}

QT_END_NAMESPACE
