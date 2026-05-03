"""Enhanced 3D Energy Sphere renderer with custom property support.

Renders a 3D energy sphere model using OpenGL, with full support for
Blender custom properties and ImGui integration.
"""

import math
import os
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

import numpy as np
import OpenGL.GL as gl
from loguru import logger


class EnergySphereParams:
    """Parameters for energy sphere animation and appearance."""
    
    def __init__(self):
        """Initialize with default values matching Blender export."""
        self.animation_time = 0.0
        self.pulse_speed = 1.0
        self.pulse_intensity = 1.0
        self.color_hue = 0.66  # Blue by default
        self.color_saturation = 1.0
        self.glow_strength = 3.0
        self.jiggle_amount = 0.0
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return {
            'animation_time': self.animation_time,
            'pulse_speed': self.pulse_speed,
            'pulse_intensity': self.pulse_intensity,
            'color_hue': self.color_hue,
            'color_saturation': self.color_saturation,
            'glow_strength': self.glow_strength,
            'jiggle_amount': self.jiggle_amount,
        }
    
    def from_dict(self, data: Dict[str, Any]):
        """Load from dictionary."""
        self.animation_time = float(data.get('animation_time', 0.0))
        self.pulse_speed = float(data.get('pulse_speed', 1.0))
        self.pulse_intensity = float(data.get('pulse_intensity', 1.0))
        self.color_hue = float(data.get('color_hue', 0.66))
        self.color_saturation = float(data.get('color_saturation', 1.0))
        self.glow_strength = float(data.get('glow_strength', 3.0))
        self.jiggle_amount = float(data.get('jiggle_amount', 0.0))
    
    @staticmethod
    def hue_to_rgb(hue: float) -> Tuple[float, float, float]:
        """Convert HSV hue to RGB (assuming S=1, V=1)."""
        h = hue * 6.0
        i = int(h)
        f = h - i
        
        if i == 0:
            return (1.0, f, 0.0)
        elif i == 1:
            return (1.0 - f, 1.0, 0.0)
        elif i == 2:
            return (0.0, 1.0, f)
        elif i == 3:
            return (0.0, 1.0 - f, 1.0)
        elif i == 4:
            return (f, 0.0, 1.0)
        else:
            return (1.0, 0.0, 1.0 - f)
    
    def get_color(self) -> Tuple[float, float, float]:
        """Get RGB color from hue and saturation."""
        rgb = self.hue_to_rgb(self.color_hue)
        # Apply saturation
        return tuple(c * self.color_saturation + (1.0 - self.color_saturation) for c in rgb)


class EnergySphereRenderer:
    """Renders 3D energy sphere with audio-responsive effects and custom properties."""

    def __init__(self):
        """Initialize energy sphere renderer."""
        self.vertices = None
        self.indices = None
        self.normals = None
        self.vao = None
        self.vbo = None
        self.ebo = None
        self.nbo = None
        self.shader_program = None
        self.model_loaded = False
        
        # Custom properties
        self.params = EnergySphereParams()
        self.custom_properties = {}

        # Get path to energy sphere model
        # Go up to src/champi_stt/assistant/ui -> src/champi_stt -> src -> assets
        self.assets_dir = Path(__file__).parent.parent.parent.parent / "assets" / "energy_sphere"
        self.model_path = self.assets_dir / "Energy_Sphere.glb"

    def load_model(self) -> bool:
        """Load the energy sphere GLB model.

        Returns:
            True if loaded successfully, False otherwise
        """
        if not self.model_path.exists():
            logger.error(f"Energy sphere model not found: {self.model_path}")
            return False

        try:
            # Try to load GLB using pygltflib
            try:
                from pygltflib import GLTF2

                gltf = GLTF2().load(str(self.model_path))
                logger.info(f"Loaded GLB model: {self.model_path}")

                # Extract custom properties if available
                self._extract_custom_properties(gltf)
                
                # Extract mesh data from GLTF
                self._extract_gltf_data(gltf)
                self.model_loaded = True
                return True

            except ImportError:
                logger.warning("pygltflib not available, falling back to simple sphere")
                # Create a simple sphere mesh as fallback
                self._create_fallback_sphere()
                self.model_loaded = True
                return True

        except Exception as e:
            logger.error(f"Failed to load energy sphere: {e}")
            # Create fallback sphere
            self._create_fallback_sphere()
            self.model_loaded = True
            return True
    
    def _extract_custom_properties(self, gltf):
        """Extract custom properties from GLTF extras.
        
        Args:
            gltf: GLTF2 object
        """
        try:
            # Check scene extras for custom properties
            if gltf.scenes and len(gltf.scenes) > 0:
                scene = gltf.scenes[0]
                if hasattr(scene, 'extras') and scene.extras:
                    logger.info(f"Found custom properties in scene extras: {scene.extras}")
                    self.params.from_dict(scene.extras)
                    self.custom_properties = scene.extras.copy()
            
            # Also check root extras
            if hasattr(gltf, 'extras') and gltf.extras:
                logger.info(f"Found custom properties in root extras: {gltf.extras}")
                self.params.from_dict(gltf.extras)
                self.custom_properties.update(gltf.extras)
            
            if self.custom_properties:
                logger.info(f"Loaded custom properties: {self.custom_properties}")
            else:
                logger.info("No custom properties found in GLB, using defaults")
                
        except Exception as e:
            logger.warning(f"Failed to extract custom properties: {e}")

    def _extract_gltf_data(self, gltf):
        """Extract mesh data from GLTF model.

        Args:
            gltf: GLTF2 object
        """
        # Get the first mesh
        mesh = gltf.meshes[0]
        primitive = mesh.primitives[0]

        # Get accessor indices
        position_accessor_idx = primitive.attributes.POSITION
        normal_accessor_idx = primitive.attributes.NORMAL if hasattr(primitive.attributes, 'NORMAL') else None
        indices_accessor_idx = primitive.indices

        # Extract vertex positions
        position_accessor = gltf.accessors[position_accessor_idx]
        position_buffer_view = gltf.bufferViews[position_accessor.bufferView]
        position_buffer = gltf.buffers[position_buffer_view.buffer]
        position_data = gltf.get_data_from_buffer_uri(position_buffer.uri)

        # Get position array
        positions = np.frombuffer(
            position_data[
                position_buffer_view.byteOffset : position_buffer_view.byteOffset
                + position_buffer_view.byteLength
            ],
            dtype=np.float32,
        ).reshape(-1, 3)

        self.vertices = positions

        # Extract normals if available
        if normal_accessor_idx is not None:
            normal_accessor = gltf.accessors[normal_accessor_idx]
            normal_buffer_view = gltf.bufferViews[normal_accessor.bufferView]
            normal_buffer = gltf.buffers[normal_buffer_view.buffer]
            normal_data = gltf.get_data_from_buffer_uri(normal_buffer.uri)

            normals = np.frombuffer(
                normal_data[
                    normal_buffer_view.byteOffset : normal_buffer_view.byteOffset
                    + normal_buffer_view.byteLength
                ],
                dtype=np.float32,
            ).reshape(-1, 3)

            self.normals = normals
        else:
            # Generate normals
            self.normals = self._generate_normals(positions)

        # Extract indices
        if indices_accessor_idx is not None:
            indices_accessor = gltf.accessors[indices_accessor_idx]
            indices_buffer_view = gltf.bufferViews[indices_accessor.bufferView]
            indices_buffer = gltf.buffers[indices_buffer_view.buffer]
            indices_data = gltf.get_data_from_buffer_uri(indices_buffer.uri)

            # Determine index type
            if indices_accessor.componentType == 5123:  # UNSIGNED_SHORT
                dtype = np.uint16
            elif indices_accessor.componentType == 5125:  # UNSIGNED_INT
                dtype = np.uint32
            else:
                dtype = np.uint16

            indices = np.frombuffer(
                indices_data[
                    indices_buffer_view.byteOffset : indices_buffer_view.byteOffset
                    + indices_buffer_view.byteLength
                ],
                dtype=dtype,
            )

            self.indices = indices

        # Log vertex bounds for debugging
        if len(self.vertices) > 0:
            v_min = self.vertices.min(axis=0)
            v_max = self.vertices.max(axis=0)
            logger.info(
                f"Vertex bounds: min={v_min}, max={v_max}, range={v_max - v_min}"
            )

        logger.info(
            f"Extracted mesh: {len(self.vertices)} vertices, "
            f"{len(self.indices) if self.indices is not None else 0} indices"
        )

    def _generate_normals(self, vertices: np.ndarray) -> np.ndarray:
        """Generate normals for vertices (assuming sphere).

        Args:
            vertices: Vertex positions

        Returns:
            Normalized normals
        """
        # For a sphere, normals point outward from center
        normals = vertices / np.linalg.norm(vertices, axis=1, keepdims=True)
        return normals.astype(np.float32)

    def _create_fallback_sphere(self, radius: float = 1.0, segments: int = 32):
        """Create a simple UV sphere as fallback.

        Args:
            radius: Sphere radius
            segments: Number of segments (resolution)
        """
        vertices = []
        normals = []
        indices = []

        # Generate sphere vertices
        for i in range(segments + 1):
            lat = math.pi * i / segments
            for j in range(segments + 1):
                lon = 2 * math.pi * j / segments

                x = radius * math.sin(lat) * math.cos(lon)
                y = radius * math.cos(lat)
                z = radius * math.sin(lat) * math.sin(lon)

                vertices.append([x, y, z])
                # For sphere, normal = normalized position
                normals.append([x, y, z])

        # Generate indices
        for i in range(segments):
            for j in range(segments):
                first = i * (segments + 1) + j
                second = first + segments + 1

                indices.extend([first, second, first + 1])
                indices.extend([second, second + 1, first + 1])

        self.vertices = np.array(vertices, dtype=np.float32)
        self.normals = np.array(normals, dtype=np.float32)
        # Normalize normals
        self.normals = self.normals / np.linalg.norm(
            self.normals, axis=1, keepdims=True
        )
        self.indices = np.array(indices, dtype=np.uint32)

        logger.info(f"Created fallback sphere: {len(self.vertices)} vertices")

    def setup_gl(self):
        """Set up OpenGL buffers and shaders."""
        if not self.model_loaded:
            logger.error("Model not loaded, cannot setup GL")
            return

        # Create VAO
        self.vao = gl.glGenVertexArrays(1)
        gl.glBindVertexArray(self.vao)

        # Create VBO for vertices
        self.vbo = gl.glGenBuffers(1)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vbo)
        gl.glBufferData(
            gl.GL_ARRAY_BUFFER,
            self.vertices.nbytes,
            self.vertices,
            gl.GL_STATIC_DRAW,
        )

        # Set vertex attribute pointer
        gl.glVertexAttribPointer(0, 3, gl.GL_FLOAT, gl.GL_FALSE, 0, None)
        gl.glEnableVertexAttribArray(0)

        # Create NBO for normals
        if self.normals is not None:
            self.nbo = gl.glGenBuffers(1)
            gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.nbo)
            gl.glBufferData(
                gl.GL_ARRAY_BUFFER,
                self.normals.nbytes,
                self.normals,
                gl.GL_STATIC_DRAW,
            )

            # Set normal attribute pointer
            gl.glVertexAttribPointer(1, 3, gl.GL_FLOAT, gl.GL_FALSE, 0, None)
            gl.glEnableVertexAttribArray(1)

        # Create EBO for indices
        if self.indices is not None:
            self.ebo = gl.glGenBuffers(1)
            gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, self.ebo)
            gl.glBufferData(
                gl.GL_ELEMENT_ARRAY_BUFFER,
                self.indices.nbytes,
                self.indices,
                gl.GL_STATIC_DRAW,
            )

        # Unbind VAO
        gl.glBindVertexArray(0)

        # Create shader program
        self._create_shaders()

        logger.info("OpenGL setup complete for energy sphere")

    def _create_shaders(self):
        """Create vertex and fragment shaders with custom property support."""
        # Vertex shader
        vertex_shader_source = """
        #version 330 core
        layout (location = 0) in vec3 aPos;
        layout (location = 1) in vec3 aNormal;

        uniform mat4 model;
        uniform mat4 view;
        uniform mat4 projection;
        uniform float animationTime;
        uniform float jiggleAmount;

        out vec3 FragPos;
        out vec3 Normal;

        void main()
        {
            // Apply jiggle animation (noise-based displacement)
            vec3 displaced = aPos;
            if (jiggleAmount > 0.0) {
                float noiseX = sin(aPos.x * 10.0 + animationTime * 2.0) * cos(aPos.y * 8.0);
                float noiseY = sin(aPos.y * 12.0 + animationTime * 2.5) * cos(aPos.z * 7.0);
                float noiseZ = sin(aPos.z * 11.0 + animationTime * 1.8) * cos(aPos.x * 9.0);
                
                displaced += aNormal * vec3(noiseX, noiseY, noiseZ) * jiggleAmount * 0.1;
            }
            
            FragPos = vec3(model * vec4(displaced, 1.0));
            Normal = mat3(transpose(inverse(model))) * aNormal;
            gl_Position = projection * view * vec4(FragPos, 1.0);
        }
        """

        # Fragment shader with procedural energy effects
        fragment_shader_source = """
        #version 330 core
        out vec4 FragColor;

        in vec3 FragPos;
        in vec3 Normal;

        uniform vec3 lightPos;
        uniform vec3 viewPos;
        uniform vec3 baseColor;
        uniform float glowStrength;
        uniform float pulseIntensity;
        uniform float animationTime;

        void main()
        {
            // Ambient
            float ambientStrength = 0.3;
            vec3 ambient = ambientStrength * baseColor;

            // Diffuse
            vec3 norm = normalize(Normal);
            vec3 lightDir = normalize(lightPos - FragPos);
            float diff = max(dot(norm, lightDir), 0.0);
            vec3 diffuse = diff * baseColor;

            // Specular (for glow effect)
            float specularStrength = 0.8;
            vec3 viewDir = normalize(viewPos - FragPos);
            vec3 reflectDir = reflect(-lightDir, norm);
            float spec = pow(max(dot(viewDir, reflectDir), 0.0), 32);
            vec3 specular = specularStrength * spec * baseColor;

            // Fresnel glow effect
            float fresnel = pow(1.0 - max(dot(viewDir, norm), 0.0), 3.0);
            
            // Animated energy waves
            float wave = sin(animationTime * 2.0 + FragPos.x * 2.0 + FragPos.y * 3.0) * 0.5 + 0.5;
            float energyPulse = wave * pulseIntensity;
            
            vec3 glow = (fresnel + energyPulse) * glowStrength * baseColor;

            // Boost brightness for better visibility
            vec3 result = (ambient + diffuse + specular + glow) * 1.5;
            FragColor = vec4(result, 1.0);
        }
        """

        # Compile shaders
        try:
            vertex_shader = gl.glCreateShader(gl.GL_VERTEX_SHADER)
            gl.glShaderSource(vertex_shader, vertex_shader_source)
            gl.glCompileShader(vertex_shader)

            # Check for compilation errors
            if not gl.glGetShaderiv(vertex_shader, gl.GL_COMPILE_STATUS):
                error = gl.glGetShaderInfoLog(vertex_shader).decode()
                logger.error(f"Vertex shader compilation failed: {error}")
                return

            fragment_shader = gl.glCreateShader(gl.GL_FRAGMENT_SHADER)
            gl.glShaderSource(fragment_shader, fragment_shader_source)
            gl.glCompileShader(fragment_shader)

            # Check for compilation errors
            if not gl.glGetShaderiv(fragment_shader, gl.GL_COMPILE_STATUS):
                error = gl.glGetShaderInfoLog(fragment_shader).decode()
                logger.error(f"Fragment shader compilation failed: {error}")
                return

            # Link shaders
            self.shader_program = gl.glCreateProgram()
            gl.glAttachShader(self.shader_program, vertex_shader)
            gl.glAttachShader(self.shader_program, fragment_shader)
            gl.glLinkProgram(self.shader_program)

            # Check for linking errors
            if not gl.glGetProgramiv(self.shader_program, gl.GL_LINK_STATUS):
                error = gl.glGetProgramInfoLog(self.shader_program).decode()
                logger.error(f"Shader program linking failed: {error}")
                return

            # Clean up shaders
            gl.glDeleteShader(vertex_shader)
            gl.glDeleteShader(fragment_shader)

            logger.info("Shaders compiled and linked successfully")

        except Exception as e:
            logger.error(f"Shader creation failed: {e}")

    def render(
        self,
        center_x: float,
        center_y: float,
        radius: float,
        window_width: int,
        window_height: int,
        audio_intensity: float = 0.0,
        x_squeeze: float = 1.0,
        y_squeeze: float = 1.0,
        override_color: Optional[Tuple[float, float, float]] = None,
    ):
        """Render the energy sphere with custom properties.

        Args:
            center_x: Center X position in screen coordinates
            center_y: Center Y position in screen coordinates
            radius: Base radius
            window_width: Window width
            window_height: Window height
            audio_intensity: Audio intensity for additional pulsing (0-1)
            x_squeeze: X-axis squeeze factor
            y_squeeze: Y-axis squeeze factor
            override_color: Optional RGB color tuple to override params color
        """
        if not self.model_loaded or self.shader_program is None:
            return

        try:
            # Use shader program
            gl.glUseProgram(self.shader_program)

            # Set up model matrix (scale, translate)
            model = np.eye(4, dtype=np.float32)

            # Apply pulse from params and audio
            pulse_factor = 1.0 + math.sin(self.params.animation_time * self.params.pulse_speed) * self.params.pulse_intensity * 0.2
            pulse_factor += audio_intensity * 0.2  # Add audio response
            
            # Scale based on radius and pulse
            scale = radius * pulse_factor
            model[0, 0] = scale * x_squeeze
            model[1, 1] = scale * y_squeeze
            model[2, 2] = scale

            # Translate to screen position
            model[3, 0] = center_x
            model[3, 1] = center_y
            model[3, 2] = 0.0

            # Identity view matrix
            view = np.eye(4, dtype=np.float32)

            # Orthographic projection for 2D screen space
            left = 0.0
            right = float(window_width)
            bottom = float(window_height)
            top = 0.0
            near = -1000.0
            far = 1000.0

            projection = np.zeros((4, 4), dtype=np.float32)
            projection[0, 0] = 2.0 / (right - left)
            projection[1, 1] = 2.0 / (top - bottom)
            projection[2, 2] = -2.0 / (far - near)
            projection[3, 3] = 1.0
            projection[0, 3] = -(right + left) / (right - left)
            projection[1, 3] = -(top + bottom) / (top - bottom)
            projection[2, 3] = -(far + near) / (far - near)

            # Send matrices to shader
            model_loc = gl.glGetUniformLocation(self.shader_program, "model")
            view_loc = gl.glGetUniformLocation(self.shader_program, "view")
            proj_loc = gl.glGetUniformLocation(self.shader_program, "projection")

            gl.glUniformMatrix4fv(model_loc, 1, gl.GL_TRUE, model)
            gl.glUniformMatrix4fv(view_loc, 1, gl.GL_TRUE, view)
            gl.glUniformMatrix4fv(proj_loc, 1, gl.GL_TRUE, projection)

            # Set custom property uniforms
            anim_time_loc = gl.glGetUniformLocation(self.shader_program, "animationTime")
            gl.glUniform1f(anim_time_loc, self.params.animation_time)
            
            jiggle_loc = gl.glGetUniformLocation(self.shader_program, "jiggleAmount")
            gl.glUniform1f(jiggle_loc, self.params.jiggle_amount)
            
            pulse_int_loc = gl.glGetUniformLocation(self.shader_program, "pulseIntensity")
            gl.glUniform1f(pulse_int_loc, self.params.pulse_intensity)
            
            glow_loc = gl.glGetUniformLocation(self.shader_program, "glowStrength")
            gl.glUniform1f(glow_loc, self.params.glow_strength)

            # Set color (use override or params)
            color = override_color if override_color else self.params.get_color()
            color_loc = gl.glGetUniformLocation(self.shader_program, "baseColor")
            gl.glUniform3f(color_loc, *color)

            # Set lighting uniforms
            light_pos_loc = gl.glGetUniformLocation(self.shader_program, "lightPos")
            gl.glUniform3f(light_pos_loc, center_x, center_y - 100, 500.0)

            view_pos_loc = gl.glGetUniformLocation(self.shader_program, "viewPos")
            gl.glUniform3f(view_pos_loc, center_x, center_y, 500.0)

            # Enable blending and depth testing
            gl.glEnable(gl.GL_BLEND)
            gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
            gl.glEnable(gl.GL_DEPTH_TEST)

            # Bind VAO and draw
            gl.glBindVertexArray(self.vao)

            if self.indices is not None:
                gl.glDrawElements(
                    gl.GL_TRIANGLES, len(self.indices), gl.GL_UNSIGNED_INT, None
                )
            else:
                gl.glDrawArrays(gl.GL_TRIANGLES, 0, len(self.vertices))

            gl.glBindVertexArray(0)

            # Disable depth test and blending
            gl.glDisable(gl.GL_DEPTH_TEST)
            gl.glDisable(gl.GL_BLEND)

        except Exception as e:
            logger.error(f"Render error: {e}")

    def cleanup(self):
        """Clean up OpenGL resources."""
        if self.vao is not None:
            gl.glDeleteVertexArrays(1, [self.vao])
        if self.vbo is not None:
            gl.glDeleteBuffers(1, [self.vbo])
        if self.ebo is not None:
            gl.glDeleteBuffers(1, [self.ebo])
        if self.nbo is not None:
            gl.glDeleteBuffers(1, [self.nbo])
        if self.shader_program is not None:
            gl.glDeleteProgram(self.shader_program)

        logger.info("Energy sphere renderer cleaned up")
