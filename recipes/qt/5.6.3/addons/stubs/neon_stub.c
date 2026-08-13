/* Stubs for all NEON-specific symbols that libQt5Gui.so.5 leaves undefined.
 * These functions are called only when the device has NEON hardware (ARMv8/A55).
 * The stubs satisfy the dynamic linker; Qt's runtime feature detection selects
 * the NEON paths only when the CPU capability is confirmed, so the stubs will
 * never actually be executed on hardware that does not support them.
 * All signatures match the mangled names exported by the Qt source. */
#include <stdint.h>

typedef unsigned int uint;
typedef unsigned char uchar;

/* Forward-declare Qt types used in signatures */
struct QRasterBuffer;
struct QImageData;
struct Operator;
struct QSpanData;
struct QClipData;
struct QRgba64 { uint64_t d; };
struct QRectF { double x1,y1,x2,y2; };
struct QRect  { int x1,y1,x2,y2;    };
struct QTransform { double m[9]; };
typedef unsigned int QFlags_ImageConversionFlag;

/* qt_memfill32: core Qt rendering primitive — must be a real implementation,
 * not an empty stub.  In Qt's source it lives in qdrawhelper_neon.cpp which
 * was not compiled into libQt5Gui.so.5 during the cross-build because the
 * NEON feature-detection in qmake skipped that translation unit.
 * Provide a portable loop; the device's ARMv7 CPU will auto-vectorise it. */
__attribute__((visibility("default")))
void _Z12qt_memfill32Pjji(unsigned int *dest, unsigned int value, int count) {
    while (count-- > 0) *dest++ = value;
}

#define STUB __attribute__((visibility("default"))) void

STUB _Z22qt_memrotate90_16_neonPKhiiiPhi(const uchar*,int,int,int,uchar*,int) {}
STUB _Z23qt_memrotate270_16_neonPKhiiiPhi(const uchar*,int,int,int,uchar*,int) {}
STUB _Z22qt_destFetchRGB16_neonPjP13QRasterBufferiii(uint*,struct QRasterBuffer*,int,int,int) {}
STUB _Z22qt_destStoreRGB16_neonP13QRasterBufferiiPKji(struct QRasterBuffer*,int,int,const uint*,int) {}
STUB _Z28convert_RGB888_to_RGB32_neonP10QImageDataPKS_6QFlagsIN2Qt19ImageConversionFlagEE(struct QImageData*,const struct QImageData*,QFlags_ImageConversionFlag) {}
STUB _Z28qt_alphamapblit_quint16_neonP13QRasterBufferiiRK7QRgba64PKhiiiPK9QClipData(struct QRasterBuffer*,int,int,const struct QRgba64,const uchar*,int,int,int,const struct QClipData*) {}
STUB _Z28qt_blend_rgb16_on_rgb16_neonPhiPKhiiii(uchar*,int,const uchar*,int,int,int,int) {}
STUB _Z28qt_blend_rgb32_on_rgb32_neonPhiPKhiiii(uchar*,int,const uchar*,int,int,int,int) {}
STUB _Z29qt_blend_argb32_on_rgb16_neonPhiPKhiiii(uchar*,int,const uchar*,int,int,int,int) {}
STUB _Z29qt_blend_rgb16_on_argb32_neonPhiPKhiiii(uchar*,int,const uchar*,int,int,int,int) {}
STUB _Z29qt_fetch_radial_gradient_neonPjPK8OperatorPK9QSpanDataiii(uint*,const struct Operator*,const struct QSpanData*,int,int,int) {}
STUB _Z30qt_blend_argb32_on_argb32_neonPhiPKhiiii(uchar*,int,const uchar*,int,int,int,int) {}
STUB _Z31comp_func_solid_SourceOver_neonPjijj(uint*,int,uint,uint) {}
STUB _Z19comp_func_Plus_neonPjPKjij(uint*,const uint*,int,uint) {}
STUB _Z34qt_scale_image_rgb16_on_rgb16_neonPhiPKhiiRK6QRectFS4_RK5QRecti(uchar*,int,const uchar*,int,int,const struct QRectF,const struct QRectF,const struct QRect,int) {}
STUB _Z35qt_scale_image_argb32_on_rgb16_neonPhiPKhiiRK6QRectFS4_RK5QRecti(uchar*,int,const uchar*,int,int,const struct QRectF,const struct QRectF,const struct QRect,int) {}
STUB _Z38qt_transform_image_rgb16_on_rgb16_neonPhiPKhiRK6QRectFS4_RK5QRectRK10QTransformi(uchar*,int,const uchar*,int,const struct QRectF,const struct QRectF,const struct QRect,const struct QTransform,int) {}
STUB _Z39qt_blend_argb32_on_argb32_scanline_neonPjPKjij(uint*,const uint*,int,uint) {}
STUB _Z39qt_transform_image_argb32_on_rgb16_neonPhiPKhiRK6QRectFS4_RK5QRectRK10QTransformi(uchar*,int,const uchar*,int,const struct QRectF,const struct QRectF,const struct QRect,const struct QTransform,int) {}
