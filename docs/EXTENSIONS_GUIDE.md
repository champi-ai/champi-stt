# Extensions Guide - Third-Party ImGui Extensions

## 1. ImGui Club Extensions

### 1.1 Memory Editor
**Repository**: https://github.com/ocornut/imgui_club

**Features**:
- Mini hexadecimal editor
- Keyboard navigation
- Read-only mode option
- ASCII/HexII display
- Goto address functionality
- Highlight range/function
- Read/Write handlers
- Right-click option menu

**MCP Tools**:
```python
# Create memory editor
add_memory_editor(
    data: bytes,
    size: int,
    base_address: int = 0,
    read_only: bool = False
)

# Configure display
set_memory_display_format(
    show_ascii: bool = True,
    show_hexii: bool = False,
    columns: int = 16
)

# Highlight operations
highlight_memory_range(
    start: int,
    end: int,
    color: tuple
)
```

### 1.2 Multi-Context Compositor
**Features**:
- Manage multiple ImGui contexts
- Z-order management
- Input routing between contexts
- Drag and drop between contexts

**MCP Tools**:
```python
# Context management
create_imgui_context(name: str)
switch_context(name: str)
set_context_z_order(name: str, z_order: int)
enable_context_drag_drop()
```

### 1.3 Threaded Rendering
**Features**:
- Snapshot ImDrawData for async rendering
- Thread-safe rendering pipeline

**MCP Tools**:
```python
# Threaded operations
capture_draw_data()
render_async(draw_data: DrawData)
```

---

## 2. Animation System (HImGuiAnimation)

### 2.1 Core Animation Features
**Repository**: https://github.com/Half-People/HImGuiAnimation

**Capabilities**:
- Keyframe-based animation
- Linear interpolation
- Minimal code implementation (<10 lines)
- No external dependencies
- Numeric value animation

**MCP Tools**:
```python
# Create animation sequence
create_animation(
    keyframes: list[int],      # Frame numbers
    values: list[float],        # Corresponding values
    name: str
)

# Interpolation
animate_value(
    animation_name: str,
    current_frame: int,
    easing: str = "linear"      # linear, ease_in, ease_out, etc.
)

# Playback control
play_animation(name: str, fps: int = 60)
pause_animation(name: str)
stop_animation(name: str)
set_animation_loop(name: str, loop: bool)

# Easing functions
set_easing_function(
    animation_name: str,
    easing: str  # linear, cubic, bounce, elastic, etc.
)
```

**Example**:
```python
# Animate button position
animation = create_animation(
    keyframes=[0, 30, 64],
    values=[80, 200, 80],
    name="button_x"
)

# In render loop
x_pos = animate_value("button_x", current_frame)
```

---

## 3. File Dialogs

### 3.1 ImGuiFD
**Repository**: https://github.com/Julianiolo/ImGuiFD

**Features**:
- No external dependencies (no STL)
- Directory selection
- ImGui-like API
- Lightweight implementation

**MCP Tools**:
```python
# File operations
open_file_dialog(
    title: str = "Open File",
    initial_path: str = ".",
    filters: list[str] = []
)

open_dir_dialog(
    title: str = "Select Directory",
    initial_path: str = "."
)

save_file_dialog(
    title: str = "Save File",
    initial_path: str = ".",
    default_name: str = "untitled"
)

# Dialog state
is_dialog_open() -> bool
get_selected_path() -> str
close_dialog()
```

### 3.2 imfile (Rust-based alternative)
**Repository**: https://github.com/tseli0s/imfile

**Features**:
- Embedded file browser
- Compatible with imgui-rs >= 0.11.0
- Configurable dialogs
- Directory-only mode

**MCP Tools**:
```python
# Advanced file dialog
create_file_dialog(
    mode: str,              # "open", "save"
    title: str = "File",
    accept_text: str = "OK",
    dir_only: bool = False
)

set_file_filters(filters: list[str])
```

---

## 4. Notifications (imgui-notify)

### 4.1 Toast Notifications
**Repository**: https://github.com/patrickcjk/imgui-notify

**Features**:
- Header-only C++ library
- Multiple notification types
- Font Awesome 5 icons
- Customizable duration
- Formatted content
- Multiline support
- Styling options

**MCP Tools**:
```python
# Notification types
show_notification(
    type: str,              # success, warning, error, info
    message: str,
    title: str = None,
    duration: int = 3000    # milliseconds
)

show_success(message: str, duration: int = 3000)
show_warning(message: str, duration: int = 3000)
show_error(message: str, duration: int = 3000)
show_info(message: str, duration: int = 3000)

# Configuration
set_notification_position(
    position: str  # top_left, top_right, bottom_left, bottom_right
)

set_notification_style(
    rounded: bool = True,
    background_alpha: float = 0.9
)

# Management
clear_notifications()
clear_notification_type(type: str)
```

---

## 5. Useful Widgets Collection

### 5.1 From ImGui Issues & Wiki
**Source**: https://github.com/ocornut/imgui/labels/useful%20widgets

**Available Widgets**:

1. **ImagePolygonButton**: Button with custom polygon shape
2. **Box Component**: Generic container widget
3. **Gradient Widgets**: Color gradient editors
4. **Texture Inspector**: ImGuiTexInspect for texture viewing
5. **Markdown Renderer**: imgui_md for markdown display
6. **Slider2D/3D**: Multi-dimensional sliders
7. **Spin Input**: Numeric spinners
8. **Editable Selectable**: Selectable with inline editing
9. **Pie Menu**: Radial menu system

**MCP Tools**:
```python
# Gradient editor
add_gradient_editor(
    id: str,
    gradient_stops: list[tuple[float, tuple]]  # [(position, color), ...]
)

# 2D/3D Sliders
add_slider_2d(
    label: str,
    value: tuple[float, float],
    min_val: tuple[float, float],
    max_val: tuple[float, float]
)

add_slider_3d(
    label: str,
    value: tuple[float, float, float],
    min_val: tuple[float, float, float],
    max_val: tuple[float, float, float]
)

# Spin input
add_spin_input(
    label: str,
    value: float,
    step: float = 1.0,
    step_fast: float = 10.0
)

# Pie menu
create_pie_menu(
    id: str,
    items: list[str],
    radius: float = 100.0
)
```

---

## 6. Advanced Extensions

### 6.1 Node Editors
- **ImNodes**: Node graph editing
- **imnodes**: Alternative implementation

**MCP Tools**:
```python
# Node editor
create_node_editor(id: str, style: str = "default")

# Node operations
add_node(
    editor_id: str,
    node_id: str,
    title: str,
    pos: tuple[float, float] = None
)

add_node_input(node_id: str, pin_id: str, label: str)
add_node_output(node_id: str, pin_id: str, label: str)

# Connections
add_link(
    editor_id: str,
    from_pin: str,
    to_pin: str
)

get_node_connections(editor_id: str) -> list
```

### 6.2 Text Editors
- **ImGuiColorTextEdit**: Syntax-highlighted editor
- **imgui-markdown**: Markdown rendering

**MCP Tools**:
```python
# Code editor
create_code_editor(
    id: str,
    language: str = "python",  # python, cpp, js, etc.
    read_only: bool = False
)

set_editor_text(editor_id: str, text: str)
get_editor_text(editor_id: str) -> str
set_syntax_highlighting(editor_id: str, enabled: bool)

# Markdown
render_markdown(
    text: str,
    font_size: int = 14
)
```

### 6.3 Plotting Extensions
**ImPlot Integration**

**MCP Tools**:
```python
# Advanced plots
add_heatmap(
    data: list[list[float]],
    label: str,
    scale_min: float,
    scale_max: float
)

add_candlestick_chart(
    dates: list,
    opens: list,
    highs: list,
    lows: list,
    closes: list
)

add_3d_surface(
    x: list,
    y: list,
    z: list[list],
    label: str
)
```

---

## 7. Custom Widget Extensions

### 7.1 Knobs
**Features**: Rotary control widgets

**MCP Tools**:
```python
add_knob(
    label: str,
    value: float,
    min_val: float,
    max_val: float,
    size: float = 40.0,
    style: str = "wiper"  # wiper, dot, stepped
)
```

### 7.2 Toggles
**Features**: Modern toggle switches

**MCP Tools**:
```python
add_toggle(
    label: str,
    value: bool,
    size: tuple[float, float] = (40, 20),
    animated: bool = True
)
```

### 7.3 Spinners
**Features**: Loading indicators

**MCP Tools**:
```python
add_spinner(
    type: str,  # circular, dots, bars, bounce
    size: float = 30.0,
    color: tuple = None
)
```

### 7.4 Date/Time Pickers
**MCP Tools**:
```python
add_date_picker(
    label: str,
    date: str = "today",  # YYYY-MM-DD
    format: str = "%Y-%m-%d"
)

add_time_picker(
    label: str,
    time: str = "now",  # HH:MM:SS
    format: str = "%H:%M:%S",
    show_seconds: bool = True
)
```

---

## 8. Integration Summary

### Total Extensions Covered:
1. ✅ imgui_club (3 extensions)
2. ✅ HImGuiAnimation (animation system)
3. ✅ ImGuiFD (file dialogs)
4. ✅ imfile (file browser)
5. ✅ imgui-notify (notifications)
6. ✅ Useful widgets collection (9+ widgets)
7. ✅ Node editors (2 implementations)
8. ✅ Text/code editors (2 types)
9. ✅ ImPlot (plotting library)
10. ✅ Custom widgets (knobs, toggles, spinners, pickers)

### MCP Tool Count from Extensions: 80+

All extensions will be accessible through the MCP server tools, allowing LLMs to create sophisticated UIs with rich functionality.
