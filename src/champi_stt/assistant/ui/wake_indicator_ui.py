"""Wake indicator UI subprocess for assistant - IPC-based floating overlay."""

import math
import os
import sys
import time
from dataclasses import dataclass

import glfw
import OpenGL.GL as gl  # noqa: N811
from imgui_bundle import imgui
from imgui_bundle.python_backends import glfw_backend
from loguru import logger

from champi_stt.assistant.ipc import (
    AssistantSharedMemoryManager,
    AssistantSignalType,
)
from champi_stt.assistant.ipc.signal_reader import AssistantSignalReader
from champi_stt.assistant.ui.energy_sphere_renderer import EnergySphereRenderer


@dataclass
class AssistantStatus:
    """Assistant status data structure."""

    state: str = "idle"  # idle, awake, recording, transcribing, executing, error
    wake_word: str = ""
    is_recording: bool = False
    partial_text: str = ""
    command: str = ""
    error_message: str = ""


class WakeIndicator:
    """Non-blocking wake indicator UI with imgui - IPC version."""

    def __init__(self, memory_manager: AssistantSharedMemoryManager):
        """Initialize wake indicator.

        Args:
            memory_manager: Shared memory manager instance
        """
        self.running = False
        self.window = None
        self.status = AssistantStatus()
        self.animation_time = 0.0
        self.impl = None

        # Audio visualization
        self.audio_rms_db = -60.0  # Current audio level in dB
        self.audio_dominant_freq = 0.0  # Dominant frequency in Hz
        self.audio_is_speaking = False  # Whether voice is detected

        # Visibility control - once shown (after wake word), stay visible until explicit hide
        self.ever_awake = False  # Has wake word been detected at least once?

        # IPC components
        self.memory_manager = memory_manager
        self.signal_reader = AssistantSignalReader(memory_manager)
        self._register_ipc_handlers()

        # 3D rendering
        self.sphere_renderer = None
        self.use_3d_sphere = True  # Try to use 3D model, fallback to 2D if fails

    def _register_ipc_handlers(self):
        """Register IPC signal handlers."""
        self.signal_reader.register_handler(
            AssistantSignalType.STATE_CHANGE, self._on_state_change
        )
        self.signal_reader.register_handler(
            AssistantSignalType.WAKE_DETECTED, self._on_wake_detected
        )
        self.signal_reader.register_handler(
            AssistantSignalType.RECORDING, self._on_recording
        )
        self.signal_reader.register_handler(
            AssistantSignalType.TRANSCRIBING, self._on_transcribing
        )
        self.signal_reader.register_handler(
            AssistantSignalType.EXECUTING, self._on_executing
        )
        self.signal_reader.register_handler(AssistantSignalType.ERROR, self._on_error)
        self.signal_reader.register_handler(
            AssistantSignalType.SHUTDOWN, self._on_shutdown
        )
        self.signal_reader.register_handler(
            AssistantSignalType.AUDIO_LEVEL, self._on_audio_level
        )

    def _on_state_change(self, signal_data):
        """Handle STATE_CHANGE signal from IPC."""
        new_state = signal_data.data.get("state", "idle")
        self.status.state = new_state
        logger.debug(f"UI: state_change - {new_state}")

        # Once wake word has been detected, stay visible
        # Only hide on explicit idle or error states that end the session
        if self.ever_awake:
            # Stay visible during listening_for_wake after being awake
            pass
        else:
            # Before first wake word, stay hidden
            if new_state in ["idle", "listening_for_wake", "initializing"]:
                self._hide_window()

    def _on_wake_detected(self, signal_data):
        """Handle WAKE_DETECTED signal from IPC."""
        self.status.state = "awake"
        self.status.wake_word = signal_data.data.get("wake_word", "")
        self.ever_awake = True  # Mark that wake word has been detected
        self._show_window()  # Ensure window is visible
        logger.debug(f"UI: wake_detected - {self.status.wake_word}")

    def _on_recording(self, signal_data):
        """Handle RECORDING signal from IPC."""
        self.status.is_recording = signal_data.data.get("is_active", False)
        if self.status.is_recording:
            self.status.state = "recording"
        logger.debug(f"UI: recording - {self.status.is_recording}")

    def _on_transcribing(self, signal_data):
        """Handle TRANSCRIBING signal from IPC."""
        self.status.state = "transcribing"
        self.status.partial_text = signal_data.data.get("partial_text", "")
        logger.debug(f"UI: transcribing - {self.status.partial_text}")

    def _on_executing(self, signal_data):
        """Handle EXECUTING signal from IPC."""
        self.status.state = "executing"
        self.status.command = signal_data.data.get("command", "")
        logger.debug(f"UI: executing - {self.status.command}")

    def _on_error(self, signal_data):
        """Handle ERROR signal from IPC."""
        self.status.state = "error"
        self.status.error_message = signal_data.data.get("error_message", "")
        logger.debug(f"UI: error - {self.status.error_message}")

    def _on_shutdown(self, signal_data):
        """Handle SHUTDOWN signal from IPC."""
        reason = signal_data.data.get("reason", "unknown")
        logger.info(f"🛑 UI: shutdown requested - reason: {reason}")
        self.running = False

    def _on_audio_level(self, signal_data):
        """Handle AUDIO_LEVEL signal from IPC."""
        self.audio_rms_db = signal_data.data.get("rms_db", -60.0)
        self.audio_dominant_freq = signal_data.data.get("dominant_freq", 0.0)
        self.audio_is_speaking = signal_data.data.get("is_speaking", False)
        logger.debug(
            f"UI: audio_level - {self.audio_rms_db:.1f}dB, "
            f"{self.audio_dominant_freq:.0f}Hz, speaking={self.audio_is_speaking}"
        )

    def init_window(self):
        """Initialize GLFW window."""
        if not glfw.init():
            raise RuntimeError("Failed to initialize GLFW")

        # Create floating window
        glfw.window_hint(hint=glfw.RESIZABLE, value=glfw.FALSE)
        glfw.window_hint(hint=glfw.DECORATED, value=glfw.FALSE)
        glfw.window_hint(hint=glfw.FLOATING, value=glfw.TRUE)
        glfw.window_hint(hint=glfw.TRANSPARENT_FRAMEBUFFER, value=glfw.TRUE)
        glfw.window_hint(hint=glfw.VISIBLE, value=glfw.FALSE)  # Start hidden

        self.window = glfw.create_window(
            width=150,
            height=150,
            title="Assistant Wake Indicator",
            monitor=None,
            share=None,
        )
        if not self.window:
            glfw.terminate()
            raise RuntimeError("Failed to create window")

        # Position window (configurable via environment variables)
        window_x = int(os.getenv("CHAMPI_ASSISTANT_UI_WINDOW_X", "50"))
        window_y = int(os.getenv("CHAMPI_ASSISTANT_UI_WINDOW_Y", "50"))
        glfw.set_window_pos(window=self.window, xpos=window_x, ypos=window_y)
        glfw.make_context_current(window=self.window)
        glfw.swap_interval(interval=1)

        imgui.create_context()
        self.impl = glfw_backend.GlfwRenderer(self.window)

        width, height = glfw.get_framebuffer_size(self.window)
        imgui.get_io().display_size = imgui.ImVec2(width, height)

        # Style for transparency
        style = imgui.get_style()
        style.window_rounding = 12.0
        style.alpha = 1

        # Initialize 3D energy sphere renderer
        if self.use_3d_sphere:
            try:
                self.sphere_renderer = EnergySphereRenderer()
                if self.sphere_renderer.load_model():
                    self.sphere_renderer.setup_gl()
                    logger.info("✅ 3D energy sphere renderer initialized")
                else:
                    logger.warning("⚠️  Failed to load 3D model, using 2D fallback")
                    self.sphere_renderer = None
            except Exception as e:
                logger.warning(
                    f"⚠️  Failed to initialize 3D renderer: {e}, using 2D fallback"
                )
                self.sphere_renderer = None

    def _show_window(self):
        """Show the window."""
        if self.window:
            glfw.show_window(self.window)

    def _hide_window(self):
        """Hide the window."""
        if self.window:
            glfw.hide_window(self.window)

    def render_status_circle(self, center_x: float, center_y: float, radius: float):
        """Render animated status circle/sphere with audio-responsive effects."""
        # Color and animation based on state
        if self.status.state == "awake":
            base_color = imgui.IM_COL32(51, 204, 51, 255)  # Green
            pulse_speed = 8
        elif self.status.state == "recording":
            base_color = imgui.IM_COL32(204, 51, 51, 255)  # Red
            pulse_speed = 6
        elif self.status.state == "transcribing":
            base_color = imgui.IM_COL32(51, 102, 204, 255)  # Blue
            pulse_speed = 4
        elif self.status.state == "executing":
            base_color = imgui.IM_COL32(204, 204, 51, 255)  # Yellow
            pulse_speed = 5
        elif self.status.state == "error":
            base_color = imgui.IM_COL32(204, 51, 51, 255)  # Red (flash)
            pulse_speed = 10
        else:  # idle
            base_color = imgui.IM_COL32(100, 100, 100, 255)  # Gray
            pulse_speed = 2

        # Calculate audio-based pulsing (decibel-driven)
        # Map dB from [-60, 0] to [0, 1] for pulse intensity
        audio_intensity = max(0.0, min(1.0, (self.audio_rms_db + 60.0) / 60.0))

        # Calculate frequency-based squeezing (tone-driven)
        # Low frequencies (100-300Hz) -> wider (x-axis stretch)
        # High frequencies (1000-3000Hz) -> taller (y-axis stretch)
        if self.audio_dominant_freq > 0:
            # Normalize frequency to [0, 1] range
            # Low: 100Hz=0, Mid: 500Hz=0.5, High: 2000Hz=1
            freq_normalized = (self.audio_dominant_freq - 100) / 1900.0
            freq_normalized = max(0.0, min(1.0, freq_normalized))

            # Low freq = x stretch, high freq = y stretch
            x_squeeze = 1.0 + (1.0 - freq_normalized) * 0.3  # 1.0-1.3
            y_squeeze = 1.0 + freq_normalized * 0.3  # 1.0-1.3
        else:
            x_squeeze = 1.0
            y_squeeze = 1.0

        # Animate radius for active states with audio influence
        if self.status.state in ["awake", "recording", "error"]:
            # Base pulse animation
            pulse = math.sin(self.animation_time * pulse_speed) * 0.4 + 1.0

            # Add audio-driven pulse when speaking
            if self.audio_is_speaking and audio_intensity > 0.1:
                pulse += audio_intensity * 0.3

            animated_radius = radius * pulse
        else:
            animated_radius = radius

        # 3D rendering is now handled in main render loop before ImGui
        # This method only handles 2D fallback when 3D is not available
        if self.sphere_renderer and self.sphere_renderer.model_loaded:
            # 3D rendering is active, skip 2D fallback
            return

        # 2D fallback rendering
        draw_list = imgui.get_window_draw_list()

        # Draw ellipse with frequency-based squeezing (instead of circle)
        # ImGui doesn't have ellipse, so we approximate with multiple segments
        if x_squeeze != 1.0 or y_squeeze != 1.0:
            # Draw custom ellipse using path
            draw_list.path_clear()
            num_segments = 32
            for i in range(num_segments + 1):
                angle = (i / num_segments) * 2 * math.pi
                x = center_x + math.cos(angle) * animated_radius * x_squeeze
                y = center_y + math.sin(angle) * animated_radius * y_squeeze
                draw_list.path_line_to(imgui.ImVec2(x, y))
            draw_list.path_fill_convex(col=base_color)

            # Draw border for active states
            if self.status.state != "idle":
                draw_list.path_clear()
                for i in range(num_segments + 1):
                    angle = (i / num_segments) * 2 * math.pi
                    x = center_x + math.cos(angle) * (animated_radius + 2) * x_squeeze
                    y = center_y + math.sin(angle) * (animated_radius + 2) * y_squeeze
                    draw_list.path_line_to(imgui.ImVec2(x, y))
                border_color = imgui.IM_COL32(255, 255, 255, 255)
                draw_list.path_stroke(col=border_color, thickness=2, closed=True)
        else:
            # Standard circle when no squeezing
            draw_list.add_circle_filled(
                center=imgui.ImVec2(center_x, center_y),
                radius=animated_radius,
                col=base_color,
            )

            # Draw border for active states
            if self.status.state != "idle":
                border_color = imgui.IM_COL32(255, 255, 255, 255)
                draw_list.add_circle(
                    center=imgui.ImVec2(center_x, center_y),
                    radius=animated_radius + 2,
                    col=border_color,
                    thickness=2,
                )

    def render_ui(self):
        """Render the main UI."""
        # Compact indicator layout
        flags = (
            imgui.WindowFlags_.no_title_bar
            | imgui.WindowFlags_.no_resize
            | imgui.WindowFlags_.no_move
            | imgui.WindowFlags_.no_background
            | imgui.WindowFlags_.no_scrollbar
        )

        imgui.set_next_window_size(size=imgui.ImVec2(150, 150))
        imgui.set_next_window_pos(pos=imgui.ImVec2(0, 0))
        imgui.set_next_window_focus()

        if imgui.begin(name="Wake Indicator", p_open=None, flags=flags):
            window_size = imgui.get_window_size()
            window_width = window_size.x
            window_height = window_size.y
            self.render_status_circle(
                center_x=window_width / 2, center_y=window_height / 2, radius=50
            )
            self._render_status_text(window_width)
        imgui.end()

    def _render_3d_sphere(self):
        """Render 3D sphere outside of ImGui context."""
        # Get window dimensions
        width, height = glfw.get_framebuffer_size(self.window)
        center_x = width / 2
        center_y = height / 2
        radius = 50

        # Calculate color based on state
        state_colors = {
            "listening_for_wake": (0.2, 0.2, 0.8),  # Blue
            "awake": (0.2, 0.8, 0.2),  # Green
            "recording": (0.8, 0.2, 0.2),  # Red
            "transcribing": (0.8, 0.6, 0.2),  # Orange
            "executing": (0.6, 0.2, 0.8),  # Purple
            "error": (0.8, 0.0, 0.0),  # Bright red
        }
        base_color_rgb = state_colors.get(self.status.state, (0.5, 0.5, 0.5))

        # Calculate audio-reactive parameters
        audio_intensity = 0.0
        if self.audio_is_speaking and self.audio_rms_db > -50:
            db_normalized = min(
                1.0, (self.audio_rms_db + 50) / 30
            )  # -50dB to -20dB -> 0 to 1
            audio_intensity = db_normalized

        # Frequency-based squeezing
        x_squeeze = 1.0
        y_squeeze = 1.0
        if self.audio_dominant_freq > 0:
            freq_normalized = min(1.0, self.audio_dominant_freq / 2000.0)
            x_squeeze = 1.0 + (1.0 - freq_normalized) * 0.3
            y_squeeze = 1.0 + freq_normalized * 0.3

        # Animate radius for active states
        pulse_speed = 2.0
        animated_radius = radius
        if self.status.state in ["awake", "recording", "error"]:
            pulse = math.sin(self.animation_time * pulse_speed) * 0.4 + 1.0
            if self.audio_is_speaking and audio_intensity > 0.1:
                pulse += audio_intensity * 0.3
            animated_radius = radius * pulse

        # Render the sphere
        self.sphere_renderer.render(
            center_x=center_x,
            center_y=center_y,
            radius=animated_radius,
            window_width=width,
            window_height=height,
            audio_intensity=audio_intensity,
            x_squeeze=x_squeeze,
            y_squeeze=y_squeeze,
            color=base_color_rgb,
        )

    def _render_status_text(self, window_width: float):
        """Render status text information."""
        # Display state text
        display_text = self.status.state.upper()
        text_size = imgui.calc_text_size(text=display_text)
        imgui.set_cursor_pos_x(local_x=(window_width - text_size.x) / 2)
        imgui.set_cursor_pos_y(local_y=110)
        imgui.text_colored(imgui.ImVec4(0.9, 0.9, 0.9, 1), display_text)

        # Context menu for testing
        if imgui.begin_popup_context_window():
            if imgui.menu_item(label="Test Awake")[0]:
                self.status.state = "awake"
            if imgui.menu_item(label="Test Recording")[0]:
                self.status.state = "recording"
            if imgui.menu_item(label="Test Transcribing")[0]:
                self.status.state = "transcribing"
            if imgui.menu_item(label="Test Error")[0]:
                self.status.state = "error"
            if imgui.menu_item(label="Reset")[0]:
                self.status = AssistantStatus()
            imgui.separator()
            if imgui.menu_item(label="Exit")[0]:
                self.running = False
            imgui.end_popup()

    def run(self):
        """Main application loop."""
        self.init_window()
        self.running = True

        logger.info("🎨 Assistant Wake Indicator started (IPC mode)")
        logger.info("📡 Listening for signals via shared memory")
        logger.info("🖱️  Right-click for test controls")

        try:
            while self.running and not glfw.window_should_close(self.window):
                # Poll IPC signals first (high priority)
                self.signal_reader.poll_once()

                # Poll GLFW events
                glfw.poll_events()
                self.impl.process_inputs()

                self.animation_time = time.time()

                # Clear buffer first
                gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)

                # Render 3D content if available (before ImGui)
                if self.sphere_renderer and self.sphere_renderer.model_loaded:
                    try:
                        self._render_3d_sphere()
                    except Exception as e:
                        logger.debug(f"3D pre-render failed: {e}")

                # Then render ImGui UI on top
                imgui.new_frame()
                self.render_ui()
                imgui.render()
                self.impl.render(imgui.get_draw_data())
                glfw.swap_buffers(self.window)

                # Minimal sleep - poll IPC as fast as possible while keeping 60 FPS rendering
                time.sleep(1 / 120)  # 120 Hz polling, but rendering still at 60 FPS

        except KeyboardInterrupt:
            logger.info("\n⚠️  Keyboard interrupt received")
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up resources."""
        self.running = False

        if hasattr(self, "signal_reader"):
            self.signal_reader.stop()

        # Clean up 3D renderer
        if hasattr(self, "sphere_renderer") and self.sphere_renderer:
            try:
                self.sphere_renderer.cleanup()
            except Exception as e:
                logger.warning(f"Error cleaning up 3D renderer: {e}")

        if hasattr(self, "impl"):
            self.impl.shutdown()

        if self.window:
            glfw.destroy_window(window=self.window)
        glfw.terminate()

        logger.info("✅ Wake Indicator cleanup complete")


def wake_indicator_main(name_prefix: str = "champi_assistant"):
    """Main entry point for IPC-based Wake Indicator subprocess.

    Args:
        name_prefix: Shared memory name prefix (e.g., "champi_assistant")
    """
    logger.info("🚀 Starting IPC-based Wake Indicator subprocess...")

    # Attach to existing shared memory
    memory_mgr = AssistantSharedMemoryManager(name_prefix=name_prefix)
    memory_mgr.attach_regions()
    logger.info(
        f"✅ Attached to {len(memory_mgr.memory_regions)} shared memory regions"
    )

    # Create and run UI
    try:
        indicator = WakeIndicator(memory_mgr)
        indicator.run()
    except Exception as e:
        logger.error(f"❌ Wake Indicator error: {e}")
        raise
    finally:
        memory_mgr.cleanup()
        logger.info("✅ Wake Indicator subprocess: Cleanup complete")


if __name__ == "__main__":
    # Can be run standalone for testing
    if len(sys.argv) > 1:
        name_prefix = sys.argv[1]
    else:
        name_prefix = "champi_assistant"
        logger.info(f"Using default name prefix: {name_prefix}")

    wake_indicator_main(name_prefix)
