

# the skyq-input protocol file
set( SKYQ_INPUT_PROTOCOL "${CMAKE_CURRENT_LIST_DIR}/../../plugins/SkyInput/protocol/skyinput.xml" )


# generate the wayland client protocol code and header files using the
# wayland-scanner host tool
generate_wayland_client_protocol(
        SKYQ_INPUT_WAYLAND_CLIENT_FILES
        BASENAME        skyq-input
        PROTOCOL        ${SKYQ_INPUT_PROTOCOL}
        WAYLAND_SCANNER ${WAYLAND_SCANNER}
        )

# generate the wayland client protocol c++ class for Qt
generate_qtwayland_client_protocol(
        SKYQ_INPUT_QTWAYLAND_CLIENT_FILES
        BASENAME          skyq-input
        PROTOCOL          ${SKYQ_INPUT_PROTOCOL}
        QTWAYLAND_SCANNER ${QTWAYLAND_SCANNER}
        )


add_library(
        skyq-input

        SHARED

        main.cpp
        qwaylandskyqinputdeviceintegration.cpp
        qwaylandskyqinputdeviceintegration_p.h
        qwaylandskyqinput.cpp
        qwaylandskyqinput.h
        qwaylandnullinputdevice.cpp
        qwaylandnullinputdevice.h

        ${SKYQ_INPUT_WAYLAND_CLIENT_FILES}
        ${SKYQ_INPUT_QTWAYLAND_CLIENT_FILES}

        )

target_include_directories(
        skyq-input

        PRIVATE
        ${Qt5WaylandClient_PRIVATE_INCLUDE_DIRS}
        $<$<BOOL:${Qt5XkbCommonSupport_FOUND}>:${Qt5XkbCommonSupport_PRIVATE_INCLUDE_DIRS}>

        )

target_link_libraries(
        skyq-input

        # Links the Qt5 libraries
        Qt5::Core
        Qt5::Gui
        Qt5::WaylandClient

        # System libraries
        Wayland::Client

        )


# the following is use to enable LTO for the plugin, which is needed to avoid
# bloated .so
target_compile_options(
        skyq-input

        PRIVATE
        -fno-exceptions
        -fvisibility=hidden
        $<$<COMPILE_LANGUAGE:CXX>:-fvisibility-inlines-hidden>
        -flto -fno-fat-lto-objects

        )

# on newer cmake versions we should use target_link_options(...) since 3.13, but
# RDK still uses cmake version 3.10 so doing it the old fashion way for now
set_target_properties(
        skyq-input

        PROPERTIES
        LINK_FLAGS "-fno-exceptions -fvisibility=hidden -fvisibility-inlines-hidden -flto=12 -fno-fat-lto-objects"

        )

# install the plugin library into the standard Qt plugin locations
install(
        TARGETS skyq-input
        DESTINATION lib/plugins/wayland-inputdevice-integration/

        )
