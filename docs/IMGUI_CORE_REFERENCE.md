# ImGui Core Reference - Complete UI Element Lists

## 1. Basic Widgets

### 1.1 Buttons
```python
# Standard buttons
imgui.button(label: str, size: ImVec2 = (0,0)) -> bool
imgui.small_button(label: str) -> bool
imgui.invisible_button(str_id: str, size: ImVec2, flags: int = 0) -> bool
imgui.arrow_button(str_id: str, dir: int) -> bool
imgui.checkbox(label: str, v: bool) -> tuple[bool, bool]
imgui.radio_button(label: str, active: bool) -> bool
```

### 1.2 Text
```python
imgui.text(text: str)
imgui.text_colored(color: ImVec4, text: str)
imgui.text_disabled(text: str)
imgui.text_wrapped(text: str)
imgui.label_text(label: str, text: str)
imgui.bullet_text(text: str)
imgui.bullet()
```

### 1.3 Input Text
```python
imgui.input_text(label: str, text: str, flags: int = 0) -> tuple[bool, str]
imgui.input_text_multiline(label: str, text: str, size: ImVec2, flags: int = 0) -> tuple[bool, str]
imgui.input_text_with_hint(label: str, hint: str, text: str, flags: int = 0) -> tuple[bool, str]
```

### 1.4 Input Numbers
```python
imgui.input_int(label: str, v: int, step: int = 1, step_fast: int = 100, flags: int = 0) -> tuple[bool, int]
imgui.input_float(label: str, v: float, step: float = 0, step_fast: float = 0, format: str = "%.3f", flags: int = 0) -> tuple[bool, float]
imgui.input_double(label: str, v: float, step: float = 0, step_fast: float = 0, format: str = "%.6f", flags: int = 0) -> tuple[bool, float]
imgui.input_scalar(label: str, data_type: int, p_data, p_step, p_step_fast, format: str, flags: int = 0)
```

---

## 2. Sliders & Drags

### 2.1 Sliders
```python
# Integer sliders
imgui.slider_int(label: str, v: int, v_min: int, v_max: int, format: str = "%d", flags: int = 0) -> tuple[bool, int]
imgui.slider_int2(label: str, v: list, v_min: int, v_max: int, format: str = "%d", flags: int = 0) -> tuple[bool, list]
imgui.slider_int3(label: str, v: list, v_min: int, v_max: int, format: str = "%d", flags: int = 0) -> tuple[bool, list]
imgui.slider_int4(label: str, v: list, v_min: int, v_max: int, format: str = "%d", flags: int = 0) -> tuple[bool, list]

# Float sliders
imgui.slider_float(label: str, v: float, v_min: float, v_max: float, format: str = "%.3f", flags: int = 0) -> tuple[bool, float]
imgui.slider_float2(label: str, v: list, v_min: float, v_max: float, format: str = "%.3f", flags: int = 0) -> tuple[bool, list]
imgui.slider_float3(label: str, v: list, v_min: float, v_max: float, format: str = "%.3f", flags: int = 0) -> tuple[bool, list]
imgui.slider_float4(label: str, v: list, v_min: float, v_max: float, format: str = "%.3f", flags: int = 0) -> tuple[bool, list]

# Special sliders
imgui.slider_angle(label: str, v_rad: float, v_degrees_min: float = -360, v_degrees_max: float = 360, format: str = "%.0f deg", flags: int = 0) -> tuple[bool, float]
imgui.v_slider_int(label: str, size: ImVec2, v: int, v_min: int, v_max: int, format: str = "%d", flags: int = 0) -> tuple[bool, int]
imgui.v_slider_float(label: str, size: ImVec2, v: float, v_min: float, v_max: float, format: str = "%.3f", flags: int = 0) -> tuple[bool, float]
```

### 2.2 Drag Controls
```python
# Integer drag
imgui.drag_int(label: str, v: int, v_speed: float = 1.0, v_min: int = 0, v_max: int = 0, format: str = "%d", flags: int = 0) -> tuple[bool, int]
imgui.drag_int2(label: str, v: list, v_speed: float = 1.0, v_min: int = 0, v_max: int = 0, format: str = "%d", flags: int = 0) -> tuple[bool, list]
imgui.drag_int3(label: str, v: list, v_speed: float = 1.0, v_min: int = 0, v_max: int = 0, format: str = "%d", flags: int = 0) -> tuple[bool, list]
imgui.drag_int4(label: str, v: list, v_speed: float = 1.0, v_min: int = 0, v_max: int = 0, format: str = "%d", flags: int = 0) -> tuple[bool, list]

# Float drag
imgui.drag_float(label: str, v: float, v_speed: float = 1.0, v_min: float = 0, v_max: float = 0, format: str = "%.3f", flags: int = 0) -> tuple[bool, float]
imgui.drag_float2(label: str, v: list, v_speed: float = 1.0, v_min: float = 0, v_max: float = 0, format: str = "%.3f", flags: int = 0) -> tuple[bool, list]
imgui.drag_float3(label: str, v: list, v_speed: float = 1.0, v_min: float = 0, v_max: float = 0, format: str = "%.3f", flags: int = 0) -> tuple[bool, list]
imgui.drag_float4(label: str, v: list, v_speed: float = 1.0, v_min: float = 0, v_max: float = 0, format: str = "%.3f", flags: int = 0) -> tuple[bool, list]

# Range drag
imgui.drag_float_range2(label: str, v_current_min: float, v_current_max: float, v_speed: float = 1.0, v_min: float = 0, v_max: float = 0, format: str = "%.3f", format_max: str = None, flags: int = 0)
imgui.drag_int_range2(label: str, v_current_min: int, v_current_max: int, v_speed: float = 1.0, v_min: int = 0, v_max: int = 0, format: str = "%d", format_max: str = None, flags: int = 0)
```

---

## 3. Color Widgets

```python
# Color edit
imgui.color_edit3(label: str, col: tuple[float, float, float], flags: int = 0) -> tuple[bool, tuple]
imgui.color_edit4(label: str, col: tuple[float, float, float, float], flags: int = 0) -> tuple[bool, tuple]

# Color picker
imgui.color_picker3(label: str, col: tuple[float, float, float], flags: int = 0) -> tuple[bool, tuple]
imgui.color_picker4(label: str, col: tuple[float, float, float, float], flags: int = 0, ref_col: tuple = None) -> tuple[bool, tuple]

# Color button
imgui.color_button(desc_id: str, col: ImVec4, flags: int = 0, size: ImVec2 = (0,0)) -> bool
```

---

## 4. Combo & Lists

```python
# Combo box
imgui.combo(label: str, current_item: int, items: list[str], popup_max_height_in_items: int = -1) -> tuple[bool, int]
imgui.begin_combo(label: str, preview_value: str, flags: int = 0) -> bool
imgui.end_combo()

# List box
imgui.list_box(label: str, current_item: int, items: list[str], height_in_items: int = -1) -> tuple[bool, int]
imgui.begin_list_box(label: str, size: ImVec2 = (0,0)) -> bool
imgui.end_list_box()

# Selectable
imgui.selectable(label: str, selected: bool = False, flags: int = 0, size: ImVec2 = (0,0)) -> tuple[bool, bool]
```

---

## 5. Tree & Hierarchy

```python
# Tree nodes
imgui.tree_node(label: str) -> bool
imgui.tree_node_ex(label: str, flags: int = 0) -> bool
imgui.tree_push(str_id: str)
imgui.tree_pop()

# Collapsing header
imgui.collapsing_header(label: str, flags: int = 0) -> bool
imgui.collapsing_header_with_close_button(label: str, visible: bool = True, flags: int = 0) -> tuple[bool, bool]

# Indent
imgui.indent(indent_w: float = 0.0)
imgui.unindent(indent_w: float = 0.0)
```

---

## 6. Tables (Advanced)

```python
# Table creation
imgui.begin_table(str_id: str, column: int, flags: int = 0, outer_size: ImVec2 = (0,0), inner_width: float = 0.0) -> bool
imgui.end_table()

# Table columns
imgui.table_next_row(row_flags: int = 0, min_row_height: float = 0.0)
imgui.table_next_column() -> bool
imgui.table_set_column_index(column_n: int) -> bool

# Table setup
imgui.table_setup_column(label: str, flags: int = 0, init_width_or_weight: float = 0.0, user_id: int = 0)
imgui.table_setup_scroll_freeze(cols: int, rows: int)
imgui.table_headers_row()
imgui.table_header(label: str)

# Table sorting
imgui.table_get_sort_specs()
imgui.table_get_column_count() -> int
imgui.table_get_column_index() -> int
imgui.table_get_row_index() -> int

# Table background
imgui.table_set_bg_color(target: int, color: int, column_n: int = -1)
```

---

## 7. Menus

```python
# Menu bar
imgui.begin_menu_bar() -> bool
imgui.end_menu_bar()
imgui.begin_main_menu_bar() -> bool
imgui.end_main_menu_bar()

# Menus
imgui.begin_menu(label: str, enabled: bool = True) -> bool
imgui.end_menu()
imgui.menu_item(label: str, shortcut: str = None, selected: bool = False, enabled: bool = True) -> tuple[bool, bool]
```

---

## 8. Tabs

```python
# Tab bar
imgui.begin_tab_bar(str_id: str, flags: int = 0) -> bool
imgui.end_tab_bar()

# Tab items
imgui.begin_tab_item(label: str, p_open: bool = None, flags: int = 0) -> tuple[bool, bool]
imgui.end_tab_item()

# Tab utilities
imgui.tab_item_button(label: str, flags: int = 0) -> bool
imgui.set_tab_item_closed(tab_or_docked_window_label: str)
```

---

## 9. Windows & Child Windows

```python
# Main windows
imgui.begin(name: str, closable: bool = None, flags: int = 0) -> tuple[bool, bool]
imgui.end()

# Child windows
imgui.begin_child(str_id: str, size: ImVec2 = (0,0), border: bool = False, flags: int = 0) -> bool
imgui.end_child()

# Window utilities
imgui.is_window_appearing() -> bool
imgui.is_window_collapsed() -> bool
imgui.is_window_focused(flags: int = 0) -> bool
imgui.is_window_hovered(flags: int = 0) -> bool
imgui.get_window_pos() -> ImVec2
imgui.get_window_size() -> ImVec2
imgui.get_window_width() -> float
imgui.get_window_height() -> float
```

---

## 10. Popups & Modals

```python
# Generic popups
imgui.begin_popup(str_id: str, flags: int = 0) -> bool
imgui.begin_popup_modal(name: str, p_open: bool = None, flags: int = 0) -> tuple[bool, bool]
imgui.end_popup()
imgui.open_popup(str_id: str, popup_flags: int = 0)
imgui.close_current_popup()

# Context menus
imgui.begin_popup_context_item(str_id: str = None, popup_flags: int = 1) -> bool
imgui.begin_popup_context_window(str_id: str = None, popup_flags: int = 1) -> bool
imgui.begin_popup_context_void(str_id: str = None, popup_flags: int = 1) -> bool

# Popup state
imgui.is_popup_open(str_id: str, flags: int = 0) -> bool
```

---

## 11. Tooltips

```python
imgui.begin_tooltip()
imgui.end_tooltip()
imgui.set_tooltip(text: str)
imgui.set_tooltip_unformatted(text: str)
```

---

## 12. Layout & Spacing

```python
# Cursor positioning
imgui.separator()
imgui.same_line(offset_from_start_x: float = 0.0, spacing: float = -1.0)
imgui.new_line()
imgui.spacing()
imgui.dummy(size: ImVec2)

# Alignment
imgui.align_text_to_frame_padding()

# Cursor manipulation
imgui.get_cursor_pos() -> ImVec2
imgui.get_cursor_pos_x() -> float
imgui.get_cursor_pos_y() -> float
imgui.set_cursor_pos(local_pos: ImVec2)
imgui.set_cursor_pos_x(local_x: float)
imgui.set_cursor_pos_y(local_y: float)
imgui.get_cursor_start_pos() -> ImVec2
imgui.get_cursor_screen_pos() -> ImVec2
imgui.set_cursor_screen_pos(pos: ImVec2)

# Item width
imgui.push_item_width(item_width: float)
imgui.pop_item_width()
imgui.set_next_item_width(item_width: float)
imgui.calc_item_width() -> float
```

---

## 13. Groups

```python
imgui.begin_group()
imgui.end_group()
```

---

## 14. Drag & Drop

```python
# Drag source
imgui.begin_drag_drop_source(flags: int = 0) -> bool
imgui.set_drag_drop_payload(type: str, data: bytes, cond: int = 0) -> bool
imgui.end_drag_drop_source()

# Drop target
imgui.begin_drag_drop_target() -> bool
imgui.accept_drag_drop_payload(type: str, flags: int = 0)
imgui.end_drag_drop_target()

# Drag drop state
imgui.get_drag_drop_payload()
```

---

## 15. Progress & Loading

```python
imgui.progress_bar(fraction: float, size_arg: ImVec2 = (-1,0), overlay: str = None)
```

---

## 16. Images & Textures

```python
imgui.image(user_texture_id, size: ImVec2, uv0: ImVec2 = (0,0), uv1: ImVec2 = (1,1), tint_col: ImVec4 = (1,1,1,1), border_col: ImVec4 = (0,0,0,0))
imgui.image_button(user_texture_id, size: ImVec2, uv0: ImVec2 = (0,0), uv1: ImVec2 = (1,1), frame_padding: int = -1, bg_col: ImVec4 = (0,0,0,0), tint_col: ImVec4 = (1,1,1,1)) -> bool
```

---

## 17. Drawing API (ImDrawList)

```python
# Get draw list
draw_list = imgui.get_window_draw_list()
draw_list = imgui.get_foreground_draw_list()
draw_list = imgui.get_background_draw_list()

# Primitives
draw_list.add_line(p1: ImVec2, p2: ImVec2, col: int, thickness: float = 1.0)
draw_list.add_rect(p_min: ImVec2, p_max: ImVec2, col: int, rounding: float = 0.0, flags: int = 0, thickness: float = 1.0)
draw_list.add_rect_filled(p_min: ImVec2, p_max: ImVec2, col: int, rounding: float = 0.0, flags: int = 0)
draw_list.add_quad(p1: ImVec2, p2: ImVec2, p3: ImVec2, p4: ImVec2, col: int, thickness: float = 1.0)
draw_list.add_quad_filled(p1: ImVec2, p2: ImVec2, p3: ImVec2, p4: ImVec2, col: int)
draw_list.add_triangle(p1: ImVec2, p2: ImVec2, p3: ImVec2, col: int, thickness: float = 1.0)
draw_list.add_triangle_filled(p1: ImVec2, p2: ImVec2, p3: ImVec2, col: int)
draw_list.add_circle(center: ImVec2, radius: float, col: int, num_segments: int = 0, thickness: float = 1.0)
draw_list.add_circle_filled(center: ImVec2, radius: float, col: int, num_segments: int = 0)
draw_list.add_ngon(center: ImVec2, radius: float, col: int, num_segments: int, thickness: float = 1.0)
draw_list.add_ngon_filled(center: ImVec2, radius: float, col: int, num_segments: int)
draw_list.add_text(pos: ImVec2, col: int, text: str)
draw_list.add_polyline(points: list[ImVec2], col: int, flags: int, thickness: float)
draw_list.add_convex_poly_filled(points: list[ImVec2], col: int)
draw_list.add_bezier_cubic(p1: ImVec2, p2: ImVec2, p3: ImVec2, p4: ImVec2, col: int, thickness: float, num_segments: int = 0)
draw_list.add_bezier_quadratic(p1: ImVec2, p2: ImVec2, p3: ImVec2, col: int, thickness: float, num_segments: int = 0)

# Image drawing
draw_list.add_image(user_texture_id, p_min: ImVec2, p_max: ImVec2, uv_min: ImVec2 = (0,0), uv_max: ImVec2 = (1,1), col: int = 0xFFFFFFFF)
draw_list.add_image_quad(user_texture_id, p1: ImVec2, p2: ImVec2, p3: ImVec2, p4: ImVec2, uv1: ImVec2 = (0,0), uv2: ImVec2 = (1,0), uv3: ImVec2 = (1,1), uv4: ImVec2 = (0,1), col: int = 0xFFFFFFFF)
draw_list.add_image_rounded(user_texture_id, p_min: ImVec2, p_max: ImVec2, uv_min: ImVec2, uv_max: ImVec2, col: int, rounding: float, flags: int = 0)

# Clipping
draw_list.push_clip_rect(clip_rect_min: ImVec2, clip_rect_max: ImVec2, intersect_with_current_clip_rect: bool = False)
draw_list.push_clip_rect_full_screen()
draw_list.pop_clip_rect()

# Paths (for advanced shapes)
draw_list.path_clear()
draw_list.path_line_to(pos: ImVec2)
draw_list.path_line_to_merge_duplicate(pos: ImVec2)
draw_list.path_fill_convex(col: int)
draw_list.path_stroke(col: int, flags: int, thickness: float = 1.0)
draw_list.path_arc_to(center: ImVec2, radius: float, a_min: float, a_max: float, num_segments: int = 0)
draw_list.path_arc_to_fast(center: ImVec2, radius: float, a_min_of_12: int, a_max_of_12: int)
draw_list.path_bezier_cubic_curve_to(p2: ImVec2, p3: ImVec2, p4: ImVec2, num_segments: int = 0)
draw_list.path_bezier_quadratic_curve_to(p2: ImVec2, p3: ImVec2, num_segments: int = 0)
draw_list.path_rect(rect_min: ImVec2, rect_max: ImVec2, rounding: float = 0.0, flags: int = 0)
```

---

## 18. Style & Colors

```python
# Style access
style = imgui.get_style()

# Push/Pop colors
imgui.push_style_color(idx: int, col: int)
imgui.push_style_color_im_vec4(idx: int, col: ImVec4)
imgui.pop_style_color(count: int = 1)

# Push/Pop style vars
imgui.push_style_var_float(idx: int, val: float)
imgui.push_style_var_im_vec2(idx: int, val: ImVec2)
imgui.pop_style_var(count: int = 1)

# Font
imgui.push_font(font)
imgui.pop_font()
imgui.get_font()
imgui.get_font_size() -> float
```

---

## 19. Input & Focus

```python
# Keyboard
imgui.is_key_down(key: int) -> bool
imgui.is_key_pressed(key: int, repeat: bool = True) -> bool
imgui.is_key_released(key: int) -> bool
imgui.get_key_pressed_amount(key: int, repeat_delay: float, rate: float) -> int

# Mouse
imgui.is_mouse_down(button: int) -> bool
imgui.is_mouse_clicked(button: int, repeat: bool = False) -> bool
imgui.is_mouse_released(button: int) -> bool
imgui.is_mouse_double_clicked(button: int) -> bool
imgui.is_mouse_hovering_rect(r_min: ImVec2, r_max: ImVec2, clip: bool = True) -> bool
imgui.is_mouse_dragging(button: int, lock_threshold: float = -1.0) -> bool
imgui.get_mouse_pos() -> ImVec2
imgui.get_mouse_pos_on_opening_current_popup() -> ImVec2
imgui.get_mouse_drag_delta(button: int = 0, lock_threshold: float = -1.0) -> ImVec2

# Focus
imgui.set_keyboard_focus_here(offset: int = 0)
imgui.is_item_focused() -> bool

# Item state
imgui.is_item_hovered(flags: int = 0) -> bool
imgui.is_item_active() -> bool
imgui.is_item_clicked(button: int = 0) -> bool
imgui.is_item_visible() -> bool
imgui.is_item_edited() -> bool
imgui.is_item_activated() -> bool
imgui.is_item_deactivated() -> bool
imgui.is_item_deactivated_after_edit() -> bool
imgui.is_item_toggled_open() -> bool
```

---

## 20. ID Stack

```python
imgui.push_id_str(str_id: str)
imgui.push_id_int(int_id: int)
imgui.push_id_ptr(ptr_id)
imgui.pop_id()
imgui.get_id(str_id: str) -> int
```

---

## Total Core ImGui Elements: 200+

This reference covers all standard ImGui widgets and APIs available in imgui-bundle for Python, providing the foundation for the MCP tool implementations.
