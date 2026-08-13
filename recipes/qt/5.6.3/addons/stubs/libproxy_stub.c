/* Minimal libproxy stub — Qt5Network needs px_proxy_factory_* at link time
 * but the widget never routes traffic via a proxy on RDK devices. */
#include <stdlib.h>

typedef struct pxProxyFactory pxProxyFactory;

__attribute__((visibility("default")))
pxProxyFactory *px_proxy_factory_new(void) { return NULL; }

__attribute__((visibility("default")))
char **px_proxy_factory_get_proxies(pxProxyFactory *f, const char *url)
{
    (void)f; (void)url;
    char **r = malloc(2 * sizeof(char *));
    if (!r) return NULL;
    r[0] = NULL; r[1] = NULL;
    return r;
}

__attribute__((visibility("default")))
void px_proxy_factory_free(pxProxyFactory *f) { (void)f; }
