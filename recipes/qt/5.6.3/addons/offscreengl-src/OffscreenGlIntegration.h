/****************************************************************************
**
** Qt 5.6.3 offscreengl platform plugin — adapted from entos-xe/qpa-offscreengl.
**
****************************************************************************/

#ifndef OFFSCREENGLINTEGRATION_H
#define OFFSCREENGLINTEGRATION_H

#include <qpa/qplatformintegration.h>
#include <qpa/qplatformscreen.h>

QT_BEGIN_NAMESPACE

class OffscreenGlScreen;

class OffscreenGlIntegration : public QPlatformIntegration
{
public:
    enum Options {
        DebugBackingStore = 0x1,
        EnableFonts       = 0x2,
        FontconfigDatabase = 0x4
    };

    explicit OffscreenGlIntegration(const QStringList &parameters);
    ~OffscreenGlIntegration();

    bool hasCapability(QPlatformIntegration::Capability cap) const Q_DECL_OVERRIDE;
    QPlatformFontDatabase *fontDatabase() const Q_DECL_OVERRIDE;

    QPlatformWindow *createPlatformWindow(QWindow *window) const Q_DECL_OVERRIDE;
    QPlatformBackingStore *createPlatformBackingStore(QWindow *window) const Q_DECL_OVERRIDE;
    QAbstractEventDispatcher *createEventDispatcher() const Q_DECL_OVERRIDE;
    QPlatformOpenGLContext *createPlatformOpenGLContext(QOpenGLContext *context) const Q_DECL_OVERRIDE;

    unsigned options() const { return m_options; }

    static OffscreenGlIntegration *instance();

private:
    mutable QPlatformFontDatabase *m_fontDatabase;
    OffscreenGlScreen *m_primaryScreen;
    unsigned m_options;
    void *m_handle; // dlopen handle for libOSMesa.so
};

QT_END_NAMESPACE

#endif // OFFSCREENGLINTEGRATION_H
