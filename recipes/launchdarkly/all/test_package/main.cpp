#include <launchdarkly/client_side/client.hpp>
#include <launchdarkly/context_builder.hpp>

#include <iostream>
#include <cstring>
#include <stdexcept>

#include <boost/beast/core.hpp>
#include <boost/beast/websocket.hpp>
#include <boost/asio/connect.hpp>
#include <boost/asio/ip/tcp.hpp>

namespace
{
void ws_connect()
{
    using tcp = boost::asio::ip::tcp;

    boost::asio::io_context ioContext;
    auto resolver = tcp::resolver(ioContext.get_executor());
    const auto results = resolver.resolve("127.0.0.1", "9998");
    auto ws = std::make_unique<boost::beast::websocket::stream<tcp::socket>>(ioContext.get_executor());
    boost::asio::connect(ws->next_layer(), results);
}
}

// Set MOBILE_KEY to your LaunchDarkly mobile key.
#define MOBILE_KEY "12345"

// Set FEATURE_FLAG_KEY to the feature flag key you want to evaluate.
#define FEATURE_FLAG_KEY "my-boolean-flag"

// Set INIT_TIMEOUT_MILLISECONDS to the amount of time you will wait for
// the client to become initialized.
#define INIT_TIMEOUT_MILLISECONDS 1000

using namespace launchdarkly;

int main() {
    try {
        // make sure that we have no binary incompatibility issues with Boost.ASIO
        // see https://github.com/launchdarkly/cpp-sdks/issues/590
        // if there are ODR violations, this will segfault
        ws_connect();
    }
    catch (const std::exception &ex) {
        std::cerr << "Error connecting to websocket: " << ex.what() << '\n';
    }

    if (!strlen(MOBILE_KEY)) {
        printf(
            "*** Please edit main.c to set MOBILE_KEY to your LaunchDarkly "
            "mobile key first\n\n");
        return 1;
    }

    auto config = client_side::ConfigBuilder(MOBILE_KEY).Build();
    if (!config) {
        std::cout << "error: config is invalid: " << config.error() << '\n';
        return 1;
    }

    auto context =
        ContextBuilder().Kind("user", "example-user-key").Name("Sandy").Build();

    auto client = client_side::Client(std::move(*config), std::move(context));

    auto start_result = client.StartAsync();
    auto status = start_result.wait_for(
        std::chrono::milliseconds(INIT_TIMEOUT_MILLISECONDS));
    if (status == std::future_status::ready) {
        if (start_result.get()) {
            std::cout << "*** SDK successfully initialized!\n\n";
        } else {
            std::cout << "*** SDK failed to initialize (this is expected)\n";
            return 0;
        }
    } else {
        std::cout << "*** SDK initialization didn't complete in "
                  << INIT_TIMEOUT_MILLISECONDS << "ms\n";
        return 0;
    }

    bool flag_value = client.BoolVariation(FEATURE_FLAG_KEY, false);

    std::cout << "*** Feature flag '" << FEATURE_FLAG_KEY << "' is "
              << (flag_value ? "true" : "false") << " for this user\n\n";

    return 0;
}
