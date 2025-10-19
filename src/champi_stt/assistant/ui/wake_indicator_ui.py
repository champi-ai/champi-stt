"""Wake indicator UI subprocess for assistant - IPC-based floating overlay."""

import math
import os
import sys
import time
from dataclasses import dataclass

import glfw
import OpenGL.GL as gl
from imgui_bundle import imgui
from imgui_bundle.python_backends import glfw_backend
from loguru import logger

from champi_stt.assistant.ipc import (
    AssistantSharedMemoryManager,
    AssistantSignalType,
)
from champi_stt.assistant.ipc.signal_reader import AssistantSignalReader


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

        # IPC components
        self.memory_manager = memory_manager
        self.signal_reader = AssistantSignalReader(memory_manager)
        self._register_ipc_handlers()

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
        self.signal_reader.register_handler(
            AssistantSignalType.ERROR, self._on_error
        )

    def _on_state_change(self, signal_data):
        """Handle STATE_CHANGE signal from IPC."""
        self.status.state = signal_data.data.get("state", "idle")
        logger.debug(f"UI: state_change - {self.status.state}")

    def _on_wake_detected(self, signal_data):
        """Handle WAKE_DETECTED signal from IPC."""
        self.status.state = "awake"
        self.status.wake_word = signal_data.data.get("wake_word", "")
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

    def init_window(self):
        """Initialize GLFW window."""
        if not glfw.init():
            raise RuntimeError("Failed to initialize GLFW")

        # Create floating window
        glfw.window_hint(hint=glfw.RESIZABLE, value=glfw.FALSE)
        glfw.window_hint(hint=glfw.DECORATED, value=glfw.FALSE)
        glfw.window_hint(hint=glfw.FLOATING, value=glfw.TRUE)
        glfw.window_hint(hint=glfw.TRANSPARENT_FRAMEBUFFER, value=glfw.TRUE)

        self.window = glfw.create_window(
            width=150, height=150, title="Assistant Wake Indicator", monitor=None, share=None
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

    def render_status_circle(self, center_x: float, center_y: float, radius: float):
        """Render animated status circle."""
        draw_list = imgui.get_window_draw_list()

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

        # Animate radius for active states
        if self.status.state in ["awake", "recording", "error"]:
            pulse = math.sin(self.animation_time * pulse_speed) * 0.4 + 1.0
            animated_radius = radius * pulse
        else:
            animated_radius = radius

        # Draw filled circle
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
                # Poll IPC signals
                self.signal_reader.poll_once()

                # Poll GLFW events
                glfw.poll_events()
                self.impl.process_inputs()

                self.animation_time = time.time()

                imgui.new_frame()
                self.render_ui()

                gl.glClear(gl.GL_COLOR_BUFFER_BIT)
                imgui.render()
                self.impl.render(imgui.get_draw_data())
                glfw.swap_buffers(self.window)

                time.sleep(1 / 60)  # 60 FPS

        except KeyboardInterrupt:
            logger.info("\n⚠️  Keyboard interrupt received")
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up resources."""
        self.running = False

        if hasattr(self, "signal_reader"):
            self.signal_reader.stop()

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
    logger.info(f"✅ Attached to {len(memory_mgr.memory_regions)} shared memory regions")

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
