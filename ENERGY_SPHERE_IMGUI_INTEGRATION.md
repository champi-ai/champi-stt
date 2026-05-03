# Energy Sphere ImGui Integration

Complete integration of the Blender energy sphere model with ImGui controls for Python OpenGL applications.

## Overview

The energy sphere is a high-quality 3D asset exported from Blender with custom properties that can be controlled in real-time through ImGui. This integration provides professional-quality animated effects for voice assistants, audio visualizers, and interactive applications.

## Files

- **energy_sphere_renderer_enhanced.py** - Enhanced renderer with custom property support
- **test_sphere_imgui.py** - Full-featured test application with ImGui controls
- **assets/energy_sphere/** - Model files (GLB, FBX, etc.)

## Features

### Custom Properties (from Blender)

The sphere includes 7 animatable custom properties:

1. **animation_time** (0.0 - ∞)
   - Global animation time counter
   - Drives all animated effects
   
2. **pulse_speed** (0.0 - 5.0)
   - Speed of pulsing animation
   - Multiplies with animation_time
   
3. **pulse_intensity** (0.0 - 2.0)
   - Strength of the pulse effect
   - 1.0 = default, 2.0 = extreme pulsing
   
4. **color_hue** (0.0 - 1.0)
   - Color hue in HSV color space
   - 0.0 = Red, 0.33 = Green, 0.66 = Blue
   
5. **color_saturation** (0.0 - 1.0)
   - Color saturation
   - 0.0 = Grayscale, 1.0 = Full color
   
6. **glow_strength** (0.0 - 10.0)
   - Intensity of the glow/emission effect
   - 3.0 = default, higher values = brighter glow
   
7. **jiggle_amount** (0.0 - 2.0)
   - Amount of noise-based vertex displacement
   - Creates organic, energy-like movement

### ImGui Controls

The test application provides full ImGui control over:

- **Animation Section**
  - Auto-animate toggle
  - Manual animation time control
  - Pulse speed slider
  - Pulse intensity slider

- **Color Section**
  - Auto color cycle toggle
  - Color hue slider
  - Color saturation slider
  - Live color preview
  - Preset colors (Blue, Green, Red, Purple)

- **Effects Section**
  - Glow strength slider
  - Jiggle amount slider

- **Actions**
  - Reset to defaults button
  - Print parameters button (outputs current values)

## Installation

### Prerequisites

```bash
# Install required packages
pip install pygltflib numpy PyOpenGL glfw imgui-bundle loguru
```

### Setup

The energy sphere model should be located at:
```
src/assets/energy_sphere/Energy_Sphere.glb
```

## Usage

### Quick Start

Run the full-featured test application:

```bash
cd /mnt/raid_0_drive/mcp_projs/libraries/champi_stt
python test_sphere_imgui.py
```

### Controls

- **ESC** - Exit application
- **C** - Toggle controls panel
- Mouse/ImGui - Adjust all parameters in real-time

### Integration Example

```python
from champi_stt.assistant.ui.energy_sphere_renderer_enhanced import (
    EnergySphereRenderer,
    EnergySphereParams,
)

# Initialize renderer
renderer = EnergySphereRenderer()
renderer.load_model()
renderer.setup_gl()

# Access and modify parameters
renderer.params.pulse_speed = 2.0
renderer.params.color_hue = 0.33  # Green
renderer.params.glow_strength = 5.0

# In your render loop
renderer.render(
    center_x=window_width / 2,
    center_y=window_height / 2,
    radius=200,
    window_width=window_width,
    window_height=window_height,
    audio_intensity=0.5,  # 0-1 from audio input
)

# Update animation time
renderer.params.animation_time += delta_time * renderer.params.pulse_speed
```

### ImGui Integration Pattern

```python
import imgui

# In your ImGui render loop
if imgui.begin("Energy Sphere"):
    # Animation controls
    _, renderer.params.pulse_speed = imgui.slider_float(
        "Pulse Speed", 
        renderer.params.pulse_speed, 
        0.0, 5.0
    )
    
    # Color controls
    _, renderer.params.color_hue = imgui.slider_float(
        "Color Hue", 
        renderer.params.color_hue, 
        0.0, 1.0
    )
    
    # Show color preview
    color = renderer.params.get_color()
    imgui.color_button(
        "Color",
        imgui.ImVec4(color[0], color[1], color[2], 1.0)
    )
    
    # Effects
    _, renderer.params.glow_strength = imgui.slider_float(
        "Glow", 
        renderer.params.glow_strength, 
        0.0, 10.0
    )

imgui.end()
```

## Shader Details

The enhanced renderer includes custom vertex and fragment shaders that implement:

### Vertex Shader
- **Jiggle Animation** - Procedural noise-based vertex displacement
- Respects `jiggle_amount` parameter
- Time-based animation using `animation_time`

### Fragment Shader
- **Fresnel Glow** - Edge-based glow effect
- **Animated Energy Waves** - Procedural wave patterns
- **Pulse Integration** - Responds to `pulse_intensity`
- **Custom Colors** - Uses `color_hue` and `color_saturation`
- **Glow Strength** - Controlled by `glow_strength` parameter

## Performance

- **Model Stats**: ~1000-2000 vertices (optimized mesh)
- **Render Time**: <1ms on modern GPUs
- **Memory**: ~5MB GPU memory
- **Recommended FPS**: 60+

## Troubleshooting

### Model Not Loading

```python
# Check if model exists
from pathlib import Path
model_path = Path("src/assets/energy_sphere/Energy_Sphere.glb")
print(f"Model exists: {model_path.exists()}")
```

### pygltflib Not Found

```bash
pip install pygltflib
```

### Black/Invisible Sphere

- Check OpenGL context is current
- Verify shaders compiled successfully (check logs)
- Ensure viewport is set correctly
- Try increasing `glow_strength` parameter

### Performance Issues

- Reduce window size
- Lower model resolution (use FBX with fewer subdivisions)
- Disable jiggle effect (`jiggle_amount = 0.0`)

## Custom Property Export

The GLB file was exported from Blender with custom properties embedded in the GLTF extras:

```json
{
  "extras": {
    "animation_time": 0.0,
    "pulse_speed": 1.0,
    "pulse_intensity": 1.0,
    "color_hue": 0.66,
    "color_saturation": 1.0,
    "glow_strength": 3.0,
    "jiggle_amount": 0.0
  }
}
```

The renderer automatically loads these values as defaults if found.

## Animation Patterns

### Breathing Effect
```python
renderer.params.pulse_speed = 0.8
renderer.params.pulse_intensity = 0.5
renderer.params.jiggle_amount = 0.0
```

### Energy Burst
```python
renderer.params.pulse_speed = 3.0
renderer.params.pulse_intensity = 1.5
renderer.params.jiggle_amount = 0.8
renderer.params.glow_strength = 8.0
```

### Calm Idle
```python
renderer.params.pulse_speed = 0.5
renderer.params.pulse_intensity = 0.3
renderer.params.jiggle_amount = 0.1
renderer.params.glow_strength = 2.0
```

### Audio Reactive
```python
# Map audio intensity (0-1) to parameters
audio = get_audio_intensity()
renderer.params.pulse_intensity = 0.5 + audio * 1.5
renderer.params.glow_strength = 2.0 + audio * 6.0
renderer.params.jiggle_amount = audio * 1.0
```

## C++ Integration

For C++ ImGui applications, refer to the original `IMGUI_INTEGRATION_GUIDE.md` in the assets folder. The same custom properties are available in FBX/GLB formats and can be accessed through Assimp or TinyGLTF.

## License

Model and integration code are part of the champi_stt project.

## Credits

- 3D model created in Blender
- Shaders optimized for real-time rendering
- ImGui integration for interactive control
