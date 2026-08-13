/****************************************************************************
**
** Qt 5.6.3 offscreengl platform plugin — adapted from entos-xe/qpa-offscreengl.
**
****************************************************************************/

#ifndef OFFSCREENGLCONTEXT_H
#define OFFSCREENGLCONTEXT_H

#include <GL/osmesa.h>
#include <qpa/qplatformopenglcontext.h>
#include <qpa/qplatformoffscreensurface.h>

#include <vector>

QT_BEGIN_NAMESPACE

class QPlatformSurface;

typedef OSMesaContext (*OSMesaCreateContextAttribsFn)(const int *attribList, OSMesaContext sharelist);
typedef void (*OSMesaDestroyContextFn)(OSMesaContext ctx);
typedef GLboolean (*OSMesaMakeCurrentFn)(OSMesaContext ctx, void *buffer, GLenum type, GLsizei width, GLsizei height);

class OffscreenGlContext : public QPlatformOpenGLContext
{
public:
    OffscreenGlContext(void *libHandle, QOpenGLContext *context);
    ~OffscreenGlContext() Q_DECL_OVERRIDE;

    QSurfaceFormat format() const Q_DECL_OVERRIDE;
    void swapBuffers(QPlatformSurface *surface) Q_DECL_OVERRIDE;
    GLuint defaultFramebufferObject(QPlatformSurface *surface) const Q_DECL_OVERRIDE;
    bool makeCurrent(QPlatformSurface *surface) Q_DECL_OVERRIDE;
    void doneCurrent() Q_DECL_OVERRIDE;
    bool isSharing() const Q_DECL_OVERRIDE;
    bool isValid() const Q_DECL_OVERRIDE;
    QFunctionPointer getProcAddress(const QByteArray &procName) Q_DECL_OVERRIDE;

private:
    OSMesaContext m_osmesaCtx;
    bool m_hasShareContext = false;
    void *m_libHandle;
    std::vector<uint8_t> m_buffer;

    OSMesaCreateContextAttribsFn OSMesaCreateContextAttribs;
    OSMesaDestroyContextFn OSMesaDestroyContext;
    OSMesaMakeCurrentFn OSMesaMakeCurrent;
};

QT_END_NAMESPACE

#endif // OFFSCREENGLCONTEXT_H
