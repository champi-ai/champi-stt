# Energy Sphere ImGui Integration

Complete integration of the Blender-exported Energy Sphere with ImGui controls.

## Overview

This integration connects the 3D energy sphere model (exported from Blender) with ImGui for real-time interactive control. All custom properties from the Blender model are exposed as ImGui-controllable parameters.

## Files

### Core Renderer
- **`energy_sphere_renderer_imgui.py`** - Enhanced renderer with ImGui parameter support
  - Extends the base renderer with Blender's custom properties
  - Auto-animates based on `pulse_speed` parameter
  - Supports all 7 custom properties from the Blender export

### Test Applications
- **`tests/test_3d_sphere_imgui.py`** - Full-featured test with ImGui controls
  - Interactive sliders for all parameters
  - Color presets (Red, Green, Blue)
  - Effect presets (High Energy, Calm, Reset)
  - Auto color cycling mode
  - Keyboard shortcuts

- **`tests/test_3d_sphere.py`** - Original simple test (for reference)

## ImGui-Controllable Parameters

All parameters match the Blender custom properties:

| Parameter | Type | Range | Default | Description |
|-----------|------|-------|---------|-------------|
| `animation_time` | float | 0+ | 0.0 | Auto-increments, drives all animations |
| `pulse_speed` | float | 0-5 | 1.0 | Speed multiplier for animation_time |
| `pulse_intensity` | float | 0-2 | 1.0 | How much the sphere pulses |
| `color_hue` | float | 0-1 | 0.66 | HSV hue (0=Red, 0.33=Green, 0.66=Blue) |
| `color_saturation` | float | 0-1 | 1.0 | Color saturation (0=white, 1=full color) |
| `glow_strength` | float | 0-10 | 3.0 | Fresnel glow intensity |
| `jiggle_amount` | float | 0-1 | 0.0 | Wavy distortion effect |

## Usage

### Basic Usage

```python
from champi_stt.assistant.ui.energy_sphere_renderer_imgui import EnergySphereImGuiRenderer

# Initialize renderer
renderer = EnergySphereImGuiRenderer()
renderer.load_model()
renderer.setup_gl()

# In your render loop
renderer.render(
    center_x=window_width / 2,
    center_y=window_height / 2,
    radius=200,
    window_width=window_width,
    window_height=window_height,
    audio_intensity=0.5,  # Optional: additional audio-reactive effect
)

# Cleanup when done
renderer.cleanup()
```

### With ImGui Controls

```python
import imgui

# In your ImGui window
if imgui.begin("Sphere Controls"):
    # Animation controls
    changed, value = imgui.slider_float("Pulse Speed", renderer.pulse_speed, 0.0, 5.0)
    if changed:
        renderer.pulse_speed = value

    changed, value = imgui.slider_float("Pulse Intensity", renderer.pulse_intensity, 0.0, 2.0)
    if changed:
        renderer.pulse_intensity = value

    # Color controls
    changed, value = imgui.slider_float("Hue", renderer.color_hue, 0.0, 1.0)
    if changed:
        renderer.color_hue = value

    changed, value = imgui.slider_float("Saturation", renderer.color_saturation, 0.0, 1.0)
    if changed:
        renderer.color_saturation = value

    # Effects
    changed, value = imgui.slider_float("Glow Strength", renderer.glow_strength, 0.0, 10.0)
    if changed:
        renderer.glow_strength = value

    changed, value = imgui.slider_float("Jiggle Amount", renderer.jiggle_amount, 0.0, 1.0)
    if changed:
        renderer.jiggle_amount = value

imgui.end()
```

### Presets

```python
# High energy preset
renderer.pulse_speed = 3.0
renderer.pulse_intensity = 1.5
renderer.glow_strength = 8.0
renderer.jiggle_amount = 0.3

# Calm preset
renderer.pulse_speed = 0.5
renderer.pulse_intensity = 0.3
renderer.glow_strength = 2.0
renderer.jiggle_amount = 0.0

# Reset to defaults
renderer.pulse_speed = 1.0
renderer.pulse_intensity = 1.0
renderer.color_hue = 0.66
renderer.color_saturation = 1.0
renderer.glow_strength = 3.0
renderer.jiggle_amount = 0.0
```

### Color Utilities

```python
# Convert HSV hue to RGB
rgb = renderer.hue_to_rgb(hue=0.66, saturation=1.0)  # Returns (0.0, 0.4, 1.0) for blue

# Color presets
renderer.color_hue = 0.66  # Blue
renderer.color_hue = 0.33  # Green
renderer.color_hue = 0.0   # Red
```

### Manual Animation Control

```python
# Auto-update (default behavior in render())
renderer.update_animation()  # Uses delta time

# Manual control
renderer.update_animation(delta_time=0.016)  # 60 FPS

# Direct control (bypasses pulse_speed)
renderer.animation_time += 0.1
```

## Running the Test

```bash
# Full ImGui controls test
python tests/test_3d_sphere_imgui.py

# Original simple test
python tests/test_3d_sphere.py
```

### Test Controls

- **ESC** - Exit
- **C** - Toggle control panel
- **Mouse** - Interact with ImGui sliders

## Shader Effects

The fragment shader implements several effects driven by the ImGui parameters:

1. **Pulsing** - Driven by `animation_time`, `pulse_speed`, and `pulse_intensity`
   - Diffuse lighting varies with a sine wave
   - Scale varies in the render function

2. **Fresnel Glow** - Controlled by `glow_strength`
   - Creates a bright rim around the sphere edges
   - More intense when viewing at grazing angles

3. **Energy Flow** - Driven by `animation_time` and `glow_strength`
   - Vertical flowing energy effect
   - Adds dynamic shimmer to the surface

4. **Jiggle Effect** - Controlled by `jiggle_amount`
   - Vertex shader distortion
   - Wavy surface deformation
   - Applied along normals

## Integration with Existing Code

To integrate with your existing `test_3d_sphere.py`:

1. Import the new renderer:
```python
from champi_stt.assistant.ui.energy_sphere_renderer_imgui import EnergySphereImGuiRenderer
```

2. Replace `EnergySphereRenderer` with `EnergySphereImGuiRenderer`

3. Add ImGui controls in your UI

4. (Optional) Remove the hardcoded color cycling and use `renderer.color_hue` instead

## Model Requirements

The renderer expects the energy sphere model at:
```
src/champi_stt/assets/energy_sphere/Energy_Sphere.glb
```

If the model is not found, it automatically creates a fallback procedural sphere.

## Dependencies

- `OpenGL`
- `numpy`
- `pygltflib` (optional, for loading GLB files)
- `imgui_bundle` (for ImGui)
- `glfw` (for windowing)
- `loguru` (for logging)

## Blender Export Details

The model was exported from Blender with these custom properties:
- Format: GLB 2.0 (single binary file)
- Features: Geometry, normals, materials (simplified)
- Custom properties: Embedded in GLTF extras (accessible via pygltflib)

## Performance Notes

- **FPS Target**: 60 FPS
- **Vertex Count**: ~3000 vertices (depends on Blender export resolution)
- **Draw Calls**: 1 per sphere
- **Shader Complexity**: Medium (fresnel, flow effects, vertex distortion)

## Troubleshooting

### Sphere not visible
- Check that `center_x`, `center_y` are within window bounds
- Ensure `radius` is appropriate for window size (try 100-300)
- Verify OpenGL context is active before calling `render()`

### Animation not working
- `animation_time` auto-updates in `render()` - don't call `render()` too infrequently
- Check that `pulse_speed` > 0
- Ensure `pulse_intensity` > 0 for visible pulsing

### Colors look wrong
- `color_hue` range is 0-1 (not 0-360)
- `color_saturation` should be 0-1
- Use `override_color` parameter if you want direct RGB control

### Performance issues
- Reduce sphere resolution (modify fallback sphere `segments` parameter)
- Lower `glow_strength` (expensive fresnel calculations)
- Disable `jiggle_amount` (vertex shader distortion)

## Future Enhancements

Potential additions:
- [ ] Particle effects around the sphere
- [ ] Multiple sphere instances
- [ ] Audio spectrum integration (FFT-based color/size)
- [ ] Texture overlay support
- [ ] Shadow rendering
- [ ] Post-processing bloom effect

## License

Matches the license of the parent project.

## Credits

- Energy Sphere model: Created in Blender 4.3.2
- Shader effects: Custom GLSL implementation
- ImGui integration: Based on imgui_bundle
