#!/usr/bin/env python3
"""Enhanced 3D energy sphere test with full ImGui controls.

This test demonstrates the Blender-exported Energy Sphere with all
custom ImGui-controllable parameters:
- animation_time (auto-updates)
- pulse_speed
- pulse_intensity
- color_hue
- color_saturation
- glow_strength
- jiggle_amount
"""

import time

import pytest

try:
    import glfw
    import OpenGL.GL as gl  # noqa: N811
    from imgui_bundle import imgui
    from imgui_bundle.python_backends import glfw_backend

    IMGUI_AVAILABLE = True
except ImportError:
    IMGUI_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not IMGUI_AVAILABLE, reason="imgui-bundle/glfw not installed"
)

from loguru import logger  # noqa: E402

if IMGUI_AVAILABLE:
    from champi_stt.assistant.ui.energy_sphere_renderer_imgui import (
        EnergySphereImGuiRenderer,
    )


def main():
    """Test the 3D sphere with full ImGui controls."""
    logger.info("Starting Enhanced 3D Sphere Test with ImGui Controls...")

    # Initialize GLFW
    if not glfw.init():
        logger.error("Failed to initialize GLFW")
        return

    # Create resizable window (800x800)
    window = glfw.create_window(
        800,
        800,
        "Energy Sphere - ImGui Integration Test",
        None,  # No monitor = windowed mode
        None,
    )
    if not window:
        glfw.terminate()
        logger.error("Failed to create window")
        return

    glfw.make_context_current(window)
    glfw.swap_interval(1)

    # Initialize ImGui
    imgui.create_context()
    impl = glfw_backend.GlfwRenderer(window)

    # Initialize sphere renderer
    sphere_renderer = EnergySphereImGuiRenderer()
    if not sphere_renderer.load_model():
        logger.error("Failed to load sphere model")
        return

    sphere_renderer.setup_gl()
    logger.info("✅ Enhanced sphere renderer initialized")

    # UI state
    show_controls = True
    audio_intensity_sim = 0.5
    auto_color_cycle = False
    start_time = time.time()

    # Main loop
    logger.info("Starting render loop... Press ESC to exit, C to toggle controls")
    while not glfw.window_should_close(window):
        glfw.poll_events()

        # Keyboard controls
        if glfw.get_key(window, glfw.KEY_ESCAPE) == glfw.PRESS:
            glfw.set_window_should_close(window, True)
        if glfw.get_key(window, glfw.KEY_C) == glfw.PRESS:
            show_controls = not show_controls
            time.sleep(0.2)  # Debounce

        impl.process_inputs()

        # Clear buffer
        gl.glClearColor(0.05, 0.05, 0.05, 1.0)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)

        # Get window size
        width, height = glfw.get_framebuffer_size(window)
        center_x = width / 2
        center_y = height / 2
        radius = 200

        # Set viewport
        gl.glViewport(0, 0, width, height)

        # Auto color cycling if enabled
        if auto_color_cycle:
            current_time = time.time() - start_time
            sphere_renderer.color_hue = (current_time * 0.1) % 1.0

        # Render sphere
        try:
            sphere_renderer.render(
                center_x=center_x,
                center_y=center_y,
                radius=radius,
                window_width=width,
                window_height=height,
                audio_intensity=audio_intensity_sim,
            )
        except Exception as e:
            logger.error(f"Render failed: {e}")
            import traceback

            logger.error(traceback.format_exc())
            break

        # Render ImGui interface
        imgui.new_frame()

        if show_controls:
            # Main control panel
            imgui.set_next_window_pos(imgui.ImVec2(20, 20))
            imgui.set_next_window_size(imgui.ImVec2(400, 550))
            if imgui.begin("⚡ Energy Sphere Controls", p_open=None):
                imgui.text_colored(
                    imgui.ImVec4(0.2, 0.8, 1.0, 1.0), "ImGui Integration Demo"
                )
                imgui.separator()

                # Animation section
                imgui.text_colored(imgui.ImVec4(1.0, 1.0, 0.2, 1.0), "🎬 Animation")
                imgui.text(f"Time: {sphere_renderer.animation_time:.2f}s")

                changed, value = imgui.slider_float(
                    "Pulse Speed", sphere_renderer.pulse_speed, 0.0, 5.0
                )
                if changed:
                    sphere_renderer.pulse_speed = value

                changed, value = imgui.slider_float(
                    "Pulse Intensity", sphere_renderer.pulse_intensity, 0.0, 2.0
                )
                if changed:
                    sphere_renderer.pulse_intensity = value

                imgui.separator()

                # Color section
                imgui.text_colored(imgui.ImVec4(1.0, 0.5, 1.0, 1.0), "🎨 Color")

                changed, auto_color_cycle = imgui.checkbox(
                    "Auto Color Cycle", auto_color_cycle
                )

                if not auto_color_cycle:
                    changed, value = imgui.slider_float(
                        "Hue", sphere_renderer.color_hue, 0.0, 1.0
                    )
                    if changed:
                        sphere_renderer.color_hue = value

                changed, value = imgui.slider_float(
                    "Saturation", sphere_renderer.color_saturation, 0.0, 1.0
                )
                if changed:
                    sphere_renderer.color_saturation = value

                # Show current color
                current_color = sphere_renderer.hue_to_rgb(
                    sphere_renderer.color_hue, sphere_renderer.color_saturation
                )
                imgui.text(
                    f"RGB: ({current_color[0]:.2f}, {current_color[1]:.2f}, {current_color[2]:.2f})"
                )

                # Color presets
                if imgui.button("🔵 Blue"):
                    sphere_renderer.color_hue = 0.66
                imgui.same_line()
                if imgui.button("🟢 Green"):
                    sphere_renderer.color_hue = 0.33
                imgui.same_line()
                if imgui.button("🔴 Red"):
                    sphere_renderer.color_hue = 0.0

                imgui.separator()

                # Effects section
                imgui.text_colored(imgui.ImVec4(0.2, 1.0, 0.5, 1.0), "✨ Effects")

                changed, value = imgui.slider_float(
                    "Glow Strength", sphere_renderer.glow_strength, 0.0, 10.0
                )
                if changed:
                    sphere_renderer.glow_strength = value

                changed, value = imgui.slider_float(
                    "Jiggle Amount", sphere_renderer.jiggle_amount, 0.0, 1.0
                )
                if changed:
                    sphere_renderer.jiggle_amount = value

                changed, value = imgui.slider_float(
                    "Audio Intensity", audio_intensity_sim, 0.0, 1.0
                )
                if changed:
                    audio_intensity_sim = value

                imgui.separator()

                # Presets
                imgui.text_colored(imgui.ImVec4(1.0, 0.8, 0.2, 1.0), "🎯 Presets")

                if imgui.button("⚡ High Energy"):
                    sphere_renderer.pulse_speed = 3.0
                    sphere_renderer.pulse_intensity = 1.5
                    sphere_renderer.glow_strength = 8.0
                    sphere_renderer.jiggle_amount = 0.3

                imgui.same_line()
                if imgui.button("😌 Calm"):
                    sphere_renderer.pulse_speed = 0.5
                    sphere_renderer.pulse_intensity = 0.3
                    sphere_renderer.glow_strength = 2.0
                    sphere_renderer.jiggle_amount = 0.0

                imgui.same_line()
                if imgui.button("🔄 Reset"):
                    sphere_renderer.pulse_speed = 1.0
                    sphere_renderer.pulse_intensity = 1.0
                    sphere_renderer.color_hue = 0.66
                    sphere_renderer.color_saturation = 1.0
                    sphere_renderer.glow_strength = 3.0
                    sphere_renderer.jiggle_amount = 0.0

                imgui.separator()
                imgui.text_colored(
                    imgui.ImVec4(0.5, 0.5, 0.5, 1.0), "Press C to toggle this panel"
                )
                imgui.text_colored(
                    imgui.ImVec4(0.5, 0.5, 0.5, 1.0), "Press ESC to exit"
                )

            imgui.end()

        # Info overlay (always visible)
        imgui.set_next_window_pos(imgui.ImVec2(width - 220, 20))
        imgui.set_next_window_size(imgui.ImVec2(200, 100))
        imgui.set_next_window_bg_alpha(0.7)
        if imgui.begin(
            "Info",
            p_open=None,
            flags=imgui.WindowFlags_.no_resize | imgui.WindowFlags_.no_title_bar,
        ):
            imgui.text("FPS: ~60")
            imgui.text(f"Window: {width}x{height}")
            imgui.text(f"Center: ({center_x:.0f}, {center_y:.0f})")
            imgui.text(f"Radius: {radius}")
        imgui.end()

        imgui.render()
        impl.render(imgui.get_draw_data())

        glfw.swap_buffers(window)
        time.sleep(1 / 60)  # 60 FPS

    # Cleanup
    logger.info("Cleaning up...")
    sphere_renderer.cleanup()
    impl.shutdown()
    glfw.terminate()
    logger.info("✅ Test complete")


if __name__ == "__main__":
    main()
