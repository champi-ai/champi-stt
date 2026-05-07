
================================================================================
ENERGY SPHERE - EXPORT PACKAGE
================================================================================

EXPORT LOCATION: /tmp/energy_sphere_exports

================================================================================
EXPORTED FILES (9 formats)
================================================================================

1. Energy_Sphere.fbx (5.7 MB)
   Format: Autodesk FBX
   Best for: Unity, Unreal Engine, Godot, Maya, 3ds Max
   Features: Full geometry, materials, modifiers applied, custom properties
   Notes: Industry standard for game engines

2. Energy_Sphere.glb (350 KB)
   Format: Binary GLTF 2.0
   Best for: Web (Three.js, Babylon.js), Mobile apps, AR/VR
   Features: Single file, optimized, PBR materials
   Notes: Recommended for web and modern 3D apps

3. Energy_Sphere.gltf + Energy_Sphere.bin (350 KB total)
   Format: GLTF 2.0 (separate files)
   Best for: Web development, inspection, editing
   Features: Human-readable JSON + binary data
   Notes: Same as GLB but with separate geometry file

4. Energy_Sphere.obj + Energy_Sphere.mtl (19.5 MB)
   Format: Wavefront OBJ
   Best for: Universal compatibility, CAD software
   Features: Basic geometry and materials
   Notes: Most widely supported format

5. Energy_Sphere.blend (1.5 MB)
   Format: Blender Native
   Best for: Blender projects, full editability
   Features: Complete setup with drivers, custom properties, materials
   Notes: Keep this for future edits!

6. Energy_Sphere.stl (12.7 MB)
   Format: STL (Stereolithography)
   Best for: 3D printing, CAD applications
   Features: Pure geometry, no materials
   Notes: High-resolution mesh for printing

7. Energy_Sphere.ply (4.8 MB)
   Format: Polygon File Format
   Best for: Point cloud, mesh processing, research
   Features: Vertex data with properties
   Notes: Good for scientific applications

================================================================================
RECOMMENDED USAGE BY PLATFORM
================================================================================

GAME ENGINES:
  Unity        → Use .fbx
  Unreal       → Use .fbx
  Godot        → Use .glb or .fbx

WEB 3D:
  Three.js     → Use .glb (best) or .gltf
  Babylon.js   → Use .glb
  A-Frame      → Use .glb

3D SOFTWARE:
  Blender      → Use .blend (keeps all features)
  Maya         → Use .fbx
  3ds Max      → Use .fbx
  Cinema 4D    → Use .fbx or .obj

AR/VR/MOBILE:
  iOS/ARKit    → Use .glb
  Android      → Use .glb
  VR Apps      → Use .glb or .fbx

3D PRINTING:
  Slicers      → Use .stl

================================================================================
IMPORTANT NOTES ABOUT CUSTOM PROPERTIES
================================================================================

The energy sphere has 7 custom properties for animation control:
  • animation_time
  • pulse_speed
  • pulse_intensity
  • color_hue
  • color_saturation
  • glow_strength
  • jiggle_amount

FORMAT SUPPORT FOR CUSTOM PROPERTIES:
  ✓ .blend  - Full support (with drivers)
  ✓ .fbx    - Custom properties exported
  ✓ .glb    - Custom properties in extras
  ✗ .obj    - No custom property support
  ✗ .stl    - Geometry only
  ✗ .ply    - Vertex data only

If you need the animation controls in your app, use .fbx or .glb and access
the custom properties through your 3D framework's API.

================================================================================
MATERIAL NOTES
================================================================================

The procedural energy material may need adjustment in some engines:

1. Emission/Glow: Most engines support emission, but you may need to:
   - Enable bloom post-processing
   - Adjust emission strength values
   - Use HDR rendering

2. Procedural Textures:
   - Blender's procedural textures (Voronoi, Noise, Wave) don't export
   - .blend file keeps procedural materials fully functional
   - Other formats use baked/simplified materials

3. For Best Visual Results:
   - Use .blend in Blender (keeps all procedural effects)
   - Use .glb for web (good PBR support)
   - Use .fbx for game engines (adjust materials in engine)

================================================================================
ACCESSING YOUR EXPORTS
================================================================================

All files are located at:
  /tmp/energy_sphere_exports

To use them:
1. The files are in Blender's temp directory
2. Copy them to your project location
3. Import into your 3D application of choice

================================================================================
