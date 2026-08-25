/*
 * glesbasevertex_shim.c
 *
 * LD_PRELOAD shim for SoCs whose GL ES driver advertises GL ES 3.1 +
 * GL_OES_draw_elements_base_vertex (or _EXT) but does NOT export the bare
 * ES 3.2 core entrypoints:
 *
 *   glDrawElementsBaseVertex
 *   glDrawRangeElementsBaseVertex
 *   glDrawElementsInstancedBaseVertex
 *
 * Symptom: the bundled Qt 5.6.3 EPG widget is linked against GLAD GLES2
 * which calls the bare names. QOpenGLContext::getProcAddress() ->
 * eglGetProcAddress() returns NULL and the renderer SEGVs on the first
 * draw call.
 *
 * Observed on Broadcom V3D (xione-sercomm: libv3ddriver.so reports
 * "OpenGL ES 3.1" and only exports the *OES / *EXT variants).
 * Not needed on Amlogic / Realtek RDK images whose Mali driver exports
 * the bare ES 3.2 names directly.
 *
 * Safety on platforms that already export the bare names:
 *   - The trampoline first asks the next library in the search chain for
 *     the BARE name (dlsym(RTLD_NEXT, "glDrawElementsBaseVertex")).  If
 *     the driver provides it the trampoline just forwards to it.
 *   - eglGetProcAddress() is interposed but always asks the real
 *     eglGetProcAddress() first and only substitutes the trampoline if
 *     the real implementation returns NULL.
 *
 * Therefore loading this shim on Amlogic / Realtek is a no-op.  The
 * launcher (run_epg.sh) gates LD_PRELOADing it on the presence of
 * /usr/lib/libv3ddriver.so as a second safety net.
 */

#include <dlfcn.h>
#include <string.h>
#include <stddef.h>

typedef unsigned int  GLenum;
typedef int           GLint;
typedef int           GLsizei;
typedef unsigned int  GLuint;
typedef void          (*__eglMustCastToProperFunctionPointerType)(void);

static void* _next(const char* name)
{
    return dlsym(RTLD_NEXT, name);
}

/* --- Trampolines exported by this library --------------------------------- */
/* On first call each trampoline resolves the best available implementation:
 *   1. driver's bare ES 3.2 name (preferred — preserves vendor behaviour)
 *   2. *OES variant   (Broadcom V3D)
 *   3. *EXT variant   (older drivers)
 * If none are found the call is a silent no-op rather than a crash.
 */

void glDrawElementsBaseVertex(GLenum mode, GLsizei count, GLenum type,
                              const void* indices, GLint basevertex)
{
    static void (*fn)(GLenum, GLsizei, GLenum, const void*, GLint) = NULL;
    static int resolved = 0;
    if (!resolved) {
        fn = _next("glDrawElementsBaseVertex");
        if (!fn) fn = _next("glDrawElementsBaseVertexOES");
        if (!fn) fn = _next("glDrawElementsBaseVertexEXT");
        resolved = 1;
    }
    if (fn) fn(mode, count, type, indices, basevertex);
}

void glDrawRangeElementsBaseVertex(GLenum mode, GLuint start, GLuint end,
                                   GLsizei count, GLenum type,
                                   const void* indices, GLint basevertex)
{
    static void (*fn)(GLenum, GLuint, GLuint, GLsizei, GLenum,
                      const void*, GLint) = NULL;
    static int resolved = 0;
    if (!resolved) {
        fn = _next("glDrawRangeElementsBaseVertex");
        if (!fn) fn = _next("glDrawRangeElementsBaseVertexOES");
        if (!fn) fn = _next("glDrawRangeElementsBaseVertexEXT");
        resolved = 1;
    }
    if (fn) fn(mode, start, end, count, type, indices, basevertex);
}

void glDrawElementsInstancedBaseVertex(GLenum mode, GLsizei count, GLenum type,
                                       const void* indices,
                                       GLsizei instancecount, GLint basevertex)
{
    static void (*fn)(GLenum, GLsizei, GLenum, const void*, GLsizei,
                      GLint) = NULL;
    static int resolved = 0;
    if (!resolved) {
        fn = _next("glDrawElementsInstancedBaseVertex");
        if (!fn) fn = _next("glDrawElementsInstancedBaseVertexOES");
        if (!fn) fn = _next("glDrawElementsInstancedBaseVertexEXT");
        resolved = 1;
    }
    if (fn) fn(mode, count, type, indices, instancecount, basevertex);
}

/* --- eglGetProcAddress interposer ----------------------------------------- */
/* Always asks the real eglGetProcAddress first.  Only substitutes our
 * trampoline if the driver returns NULL for one of the bare ES 3.2 names.
 * This means callers on platforms that already export the bare names get
 * the driver function and the shim never enters the picture.
 */

struct alias { const char* name; void* fn; };

__eglMustCastToProperFunctionPointerType
eglGetProcAddress(const char* procname)
{
    static __eglMustCastToProperFunctionPointerType
        (*real_eglGetProcAddress)(const char*) = NULL;
    if (!real_eglGetProcAddress) {
        real_eglGetProcAddress =
            (__eglMustCastToProperFunctionPointerType (*)(const char*))
                _next("eglGetProcAddress");
    }

    __eglMustCastToProperFunctionPointerType driver_fn =
        real_eglGetProcAddress ? real_eglGetProcAddress(procname) : NULL;
    if (driver_fn || !procname) {
        return driver_fn;
    }

    static const struct alias aliases[] = {
        { "glDrawElementsBaseVertex",
          (void*)glDrawElementsBaseVertex },
        { "glDrawRangeElementsBaseVertex",
          (void*)glDrawRangeElementsBaseVertex },
        { "glDrawElementsInstancedBaseVertex",
          (void*)glDrawElementsInstancedBaseVertex },
    };
    for (size_t i = 0; i < sizeof(aliases) / sizeof(aliases[0]); ++i) {
        if (strcmp(procname, aliases[i].name) == 0) {
            return (__eglMustCastToProperFunctionPointerType) aliases[i].fn;
        }
    }
    return NULL;
}
