# offscreengl.pro — Qt 5.6.3 platform plugin using OSMesa (no X11/EGL needed)
TARGET = offscreengl
TEMPLATE = lib
CONFIG += plugin

DEFINES += QT_NO_FOREACH

SOURCES = main.cpp \
          OffscreenGlIntegration.cpp \
          OffscreenGlContext.cpp \
          OffscreenGlBackingstore.cpp \
          OffscreenGlScreen.cpp \
          OffscreenGlWindow.cpp

HEADERS = OffscreenGlIntegration.h \
          OffscreenGlContext.h \
          OffscreenGlBackingstore.h \
          OffscreenGlScreen.h \
          OffscreenGlWindow.h

OTHER_FILES += offscreengl.json

PLUGIN_TYPE = platforms
PLUGIN_CLASS_NAME = OffscreenGlIntegrationPlugin

load(qt_plugin)

QT += core-private gui-private platformsupport-private
LIBS += -ldl
# OSMesa is loaded at runtime via dlopen/dlsym — no link-time dependency needed.
# --as-needed drops any transitive .prl deps that our plugin doesn't actually call
# (fontconfig, freetype, EGL, Xrender) so they don't appear in DT_NEEDED and the
# plugin loads cleanly even when those -dev/-runtime packages are absent.
QMAKE_LFLAGS += -Wl,--as-needed
