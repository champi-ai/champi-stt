"""3D Energy Sphere renderer with ImGui controls for Blender-exported model.

Renders a 3D energy sphere model using OpenGL, with ImGui-controllable parameters
matching the custom properties from the Blender export.
"""

import math
import time
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import OpenGL.GL as gl
from loguru import logger


class EnergySphereImGuiRenderer:
    """Renders 3D energy sphere with ImGui-controllable parameters.
    
    This renderer integrates with the Blender-exported Energy Sphere model
    and provides ImGui controls for all custom properties:
    - animation_time
    - pulse_speed
    - pulse_intensity
    - color_hue
    - color_saturation
    - glow_strength
    - jiggle_amount
    """

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

        # ImGui-controllable parameters (matching Blender custom properties)
        self.animation_time = 0.0
        self.pulse_speed = 1.0
        self.pulse_intensity = 1.0
        self.color_hue = 0.66  # Blue by default
        self.color_saturation = 1.0
        self.glow_strength = 3.0
        self.jiggle_amount = 0.0
        
        # Internal state
        self._start_time = time.time()
        self._last_update = time.time()

        # Get path to energy sphere model
        self.assets_dir = Path(__file__).parent.parent.parent.parent / "assets" / "energy_sphere"
        self.model_path = self.assets_dir / "Energy_Sphere.glb"
        
        logger.info(f"Energy Sphere ImGui Renderer initialized")
        logger.info(f"Model path: {self.model_path}")

    def load_model(self) -> bool:
        """Load the energy sphere GLB model.

        Returns:
            True if loaded successfully, False otherwise
        """
        if not self.model_path.exists():
            logger.error(f"Energy sphere model not found: {self.model_path}")
            logger.info("Creating fallback sphere...")
            self._create_fallback_sphere()
            self.model_loaded = True
            return True

        try:
            # Try to load GLB using pygltflib
            try:
                from pygltflib import GLTF2

                gltf = GLTF2().load(str(self.model_path))
                logger.info(f"✅ Loaded GLB model: {self.model_path}")

                # Extract mesh data from GLTF
                self._extract_gltf_data(gltf)
                self.model_loaded = True
                return True

            except ImportError:
                logger.warning("pygltflib not available, falling back to simple sphere")
                self._create_fallback_sphere()
                self.model_loaded = True
                return True

        except Exception as e:
            logger.error(f"Failed to load energy sphere: {e}")
            self._create_fallback_sphere()
            self.model_loaded = True
            return True

    def _extract_gltf_data(self, gltf):
        """Extract mesh data from GLTF model (copied from base renderer)."""
        mesh = gltf.meshes[0]
        primitive = mesh.primitives[0]

        position_accessor_idx = primitive.attributes.POSITION
        normal_accessor_idx = primitive.attributes.NORMAL if hasattr(primitive.attributes, 'NORMAL') else None
        indices_accessor_idx = primitive.indices

        # Extract vertex positions
        position_accessor = gltf.accessors[position_accessor_idx]
        position_buffer_view = gltf.bufferViews[position_accessor.bufferView]
        position_buffer = gltf.buffers[position_buffer_view.buffer]
        position_data = gltf.get_data_from_buffer_uri(position_buffer.uri)

        positions = np.frombuffer(
            position_data[position_buffer_view.byteOffset : position_buffer_view.byteOffset + position_buffer_view.byteLength],
            dtype=np.float32,
        ).reshape(-1, 3)
        self.vertices = positions

        # Extract normals
        if normal_accessor_idx is not None:
            normal_accessor = gltf.accessors[normal_accessor_idx]
            normal_buffer_view = gltf.bufferViews[normal_accessor.bufferView]
            normal_buffer = gltf.buffers[normal_buffer_view.buffer]
            normal_data = gltf.get_data_from_buffer_uri(normal_buffer.uri)

            normals = np.frombuffer(
                normal_data[normal_buffer_view.byteOffset : normal_buffer_view.byteOffset + normal_buffer_view.byteLength],
                dtype=np.float32,
            ).reshape(-1, 3)
            self.normals = normals
        else:
            self.normals = self._generate_normals(positions)

        # Extract indices
        if indices_accessor_idx is not None:
            indices_accessor = gltf.accessors[indices_accessor_idx]
            indices_buffer_view = gltf.bufferViews[indices_accessor.bufferView]
            indices_buffer = gltf.buffers[indices_buffer_view.buffer]
            indices_data = gltf.get_data_from_buffer_uri(indices_buffer.uri)

            dtype = np.uint16 if indices_accessor.componentType == 5123 else np.uint32
            indices = np.frombuffer(
                indices_data[indices_buffer_view.byteOffset : indices_buffer_view.byteOffset + indices_buffer_view.byteLength],
                dtype=dtype,
            )
            self.indices = indices

        logger.info(f"Mesh data: {len(self.vertices)} vertices, {len(self.indices) if self.indices is not None else 0} indices")

    def _generate_normals(self, vertices: np.ndarray) -> np.ndarray:
        """Generate normals for vertices (sphere normals point outward)."""
        normals = vertices / np.linalg.norm(vertices, axis=1, keepdims=True)
        return normals.astype(np.float32)

    def _create_fallback_sphere(self, radius: float = 1.0, segments: int = 32):
        """Create a simple UV sphere as fallback."""
        vertices, normals, indices = [], [], []

        for i in range(segments + 1):
            lat = math.pi * i / segments
            for j in range(segments + 1):
                lon = 2 * math.pi * j / segments
                x = radius * math.sin(lat) * math.cos(lon)
                y = radius * math.cos(lat)
                z = radius * math.sin(lat) * math.sin(lon)
                vertices.append([x, y, z])
                normals.append([x, y, z])

        for i in range(segments):
            for j in range(segments):
                first = i * (segments + 1) + j
                second = first + segments + 1
                indices.extend([first, second, first + 1, second, second + 1, first + 1])

        self.vertices = np.array(vertices, dtype=np.float32)
        self.normals = np.array(normals, dtype=np.float32)
        self.normals = self.normals / np.linalg.norm(self.normals, axis=1, keepdims=True)
        self.indices = np.array(indices, dtype=np.uint32)
        logger.info(f"Created fallback sphere: {len(self.vertices)} vertices")

    def update_animation(self, delta_time: Optional[float] = None):
        """Update animation time based on pulse_speed.
        
        Args:
            delta_time: Time delta in seconds. If None, auto-calculates from last update.
        """
        if delta_time is None:
            current_time = time.time()
            delta_time = current_time - self._last_update
            self._last_update = current_time
        
        # Update animation time based on pulse speed
        self.animation_time += delta_time * self.pulse_speed
    
    def hue_to_rgb(self, hue: float, saturation: float = 1.0) -> Tuple[float, float, float]:
        """Convert HSV to RGB (Value=1.0).
        
        Args:
            hue: Hue value (0-1)
            saturation: Saturation (0-1)
            
        Returns:
            RGB tuple (0-1 range)
        """
        hue = hue % 1.0
        h = hue * 6.0
        x = 1.0 - abs((h % 2.0) - 1.0)
        
        if h < 1:
            r, g, b = 1, x, 0
        elif h < 2:
            r, g, b = x, 1, 0
        elif h < 3:
            r, g, b = 0, 1, x
        elif h < 4:
            r, g, b = 0, x, 1
        elif h < 5:
            r, g, b = x, 0, 1
        else:
            r, g, b = 1, 0, x
        
        # Apply saturation
        r = r * saturation + (1 - saturation)
        g = g * saturation + (1 - saturation)
        b = b * saturation + (1 - saturation)
        
        return (r, g, b)

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
        gl.glBufferData(gl.GL_ARRAY_BUFFER, self.vertices.nbytes, self.vertices, gl.GL_STATIC_DRAW)
        gl.glVertexAttribPointer(0, 3, gl.GL_FLOAT, gl.GL_FALSE, 0, None)
        gl.glEnableVertexAttribArray(0)

        # Create NBO for normals
        if self.normals is not None:
            self.nbo = gl.glGenBuffers(1)
            gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.nbo)
            gl.glBufferData(gl.GL_ARRAY_BUFFER, self.normals.nbytes, self.normals, gl.GL_STATIC_DRAW)
            gl.glVertexAttribPointer(1, 3, gl.GL_FLOAT, gl.GL_FALSE, 0, None)
            gl.glEnableVertexAttribArray(1)

        # Create EBO for indices
        if self.indices is not None:
            self.ebo = gl.glGenBuffers(1)
            gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, self.ebo)
            gl.glBufferData(gl.GL_ELEMENT_ARRAY_BUFFER, self.indices.nbytes, self.indices, gl.GL_STATIC_DRAW)

        gl.glBindVertexArray(0)
        self._create_shaders()
        logger.info("✅ OpenGL setup complete for energy sphere")

    def _create_shaders(self):
        """Create vertex and fragment shaders with enhanced effects."""
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
        out float VTime;

        void main()
        {
            vec3 pos = aPos;

            // Apply jiggle effect (wavy distortion)
            if (jiggleAmount > 0.0) {
                float jiggle = sin(animationTime * 5.0 + pos.x * 3.0) * cos(animationTime * 3.0 + pos.y * 4.0);
                pos += aNormal * jiggle * jiggleAmount * 0.1;
            }

            // Transform to world space for lighting calculations
            FragPos = vec3(model * vec4(pos, 1.0));
            Normal = mat3(transpose(inverse(model))) * aNormal;
            VTime = animationTime;

            // FIXED: Transform from local space directly to clip space
            gl_Position = projection * view * model * vec4(pos, 1.0);
        }
        """

        fragment_shader_source = """
        #version 330 core
        out vec4 FragColor;

        in vec3 FragPos;
        in vec3 Normal;
        in float VTime;

        uniform vec3 lightPos;
        uniform vec3 viewPos;
        uniform vec3 objectColor;
        uniform float glowStrength;
        uniform float pulseIntensity;

        void main()
        {
            // DEBUG: Output solid bright magenta to test visibility
            FragColor = vec4(1.0, 0.0, 1.0, 1.0);  // Bright magenta

            // TODO: Restore original shader after confirming visibility
            /*
            // Ambient
            float ambientStrength = 0.3;
            vec3 ambient = ambientStrength * objectColor;

            // Diffuse with pulsing
            vec3 norm = normalize(Normal);
            vec3 lightDir = normalize(lightPos - FragPos);
            float diff = max(dot(norm, lightDir), 0.0);
            float pulse = sin(VTime * 2.0) * 0.5 + 0.5;
            diff = diff * (1.0 + pulse * pulseIntensity * 0.5);
            vec3 diffuse = diff * objectColor;

            // Specular (for glow effect)
            float specularStrength = 0.8;
            vec3 viewDir = normalize(viewPos - FragPos);
            vec3 reflectDir = reflect(-lightDir, norm);
            float spec = pow(max(dot(viewDir, reflectDir), 0.0), 32);
            vec3 specular = specularStrength * spec * objectColor;

            // Fresnel glow effect (enhanced with glowStrength)
            float fresnel = pow(1.0 - max(dot(viewDir, norm), 0.0), 3.0);
            vec3 glow = fresnel * glowStrength * objectColor;

            // Energy flow effect
            float flow = sin(VTime * 3.0 + FragPos.y * 0.1) * 0.5 + 0.5;
            vec3 energyGlow = flow * glowStrength * 0.3 * objectColor;

            // Combine all effects
            vec3 result = (ambient + diffuse + specular + glow + energyGlow) * 1.5;
            FragColor = vec4(result, 1.0);
            */
        }
        """

        try:
            vertex_shader = gl.glCreateShader(gl.GL_VERTEX_SHADER)
            gl.glShaderSource(vertex_shader, vertex_shader_source)
            gl.glCompileShader(vertex_shader)

            if not gl.glGetShaderiv(vertex_shader, gl.GL_COMPILE_STATUS):
                error = gl.glGetShaderInfoLog(vertex_shader).decode()
                logger.error(f"Vertex shader compilation failed: {error}")
                return

            fragment_shader = gl.glCreateShader(gl.GL_FRAGMENT_SHADER)
            gl.glShaderSource(fragment_shader, fragment_shader_source)
            gl.glCompileShader(fragment_shader)

            if not gl.glGetShaderiv(fragment_shader, gl.GL_COMPILE_STATUS):
                error = gl.glGetShaderInfoLog(fragment_shader).decode()
                logger.error(f"Fragment shader compilation failed: {error}")
                return

            self.shader_program = gl.glCreateProgram()
            gl.glAttachShader(self.shader_program, vertex_shader)
            gl.glAttachShader(self.shader_program, fragment_shader)
            gl.glLinkProgram(self.shader_program)

            if not gl.glGetProgramiv(self.shader_program, gl.GL_LINK_STATUS):
                error = gl.glGetProgramInfoLog(self.shader_program).decode()
                logger.error(f"Shader program linking failed: {error}")
                return

            gl.glDeleteShader(vertex_shader)
            gl.glDeleteShader(fragment_shader)
            logger.info("✅ Shaders compiled and linked successfully")

        except Exception as e:
            logger.error(f"Shader creation failed: {e}")

    def render(self,
               center_x: float,
               center_y: float,
               radius: float,
               window_width: int,
               window_height: int,
               audio_intensity: float = 0.0,
               x_squeeze: float = 1.0,
               y_squeeze: float = 1.0,
               override_color: Optional[Tuple[float, float, float]] = None):
        """Render the energy sphere with ImGui parameters.

        Args:
            center_x: Center X position in screen coordinates
            center_y: Center Y position in screen coordinates  
            radius: Base radius
            window_width: Window width
            window_height: Window height
            audio_intensity: Audio intensity for additional effects (0-1)
            x_squeeze: X-axis squeeze factor
            y_squeeze: Y-axis squeeze factor
            override_color: Optional color override (otherwise uses color_hue/saturation)
        """
        if not self.model_loaded or self.shader_program is None:
            return

        # Auto-update animation time
        self.update_animation()

        # Get color from hue/saturation or use override
        if override_color is not None:
            color = override_color
        else:
            color = self.hue_to_rgb(self.color_hue, self.color_saturation)

        gl.glUseProgram(self.shader_program)

        # Model matrix with pulsing (row-major NumPy format, will be transposed by GL_TRUE)
        model = np.eye(4, dtype=np.float32)
        pulse = math.sin(self.animation_time * 2.0) * 0.5 + 0.5
        scale_factor = radius * (1.0 + pulse * self.pulse_intensity * 0.3 + audio_intensity * 0.2)

        model[0, 0] = scale_factor * x_squeeze
        model[1, 1] = scale_factor * y_squeeze
        model[2, 2] = scale_factor
        model[3, 0] = center_x  # Translation in row 3 (row-major, will transpose to column 3)
        model[3, 1] = center_y
        model[3, 2] = 0.0


        # View matrix
        view = np.eye(4, dtype=np.float32)

        # Orthographic projection
        left, right = 0.0, float(window_width)
        bottom, top = float(window_height), 0.0
        near, far = -1000.0, 1000.0

        projection = np.zeros((4, 4), dtype=np.float32)
        projection[0, 0] = 2.0 / (right - left)
        projection[1, 1] = 2.0 / (top - bottom)
        projection[2, 2] = -2.0 / (far - near)
        projection[3, 3] = 1.0
        projection[0, 3] = -(right + left) / (right - left)
        projection[1, 3] = -(top + bottom) / (top - bottom)
        projection[2, 3] = -(far + near) / (far - near)


        # Send matrices to shader (GL_TRUE = transpose from NumPy row-major to OpenGL column-major)
        model_loc = gl.glGetUniformLocation(self.shader_program, "model")
        view_loc = gl.glGetUniformLocation(self.shader_program, "view")
        proj_loc = gl.glGetUniformLocation(self.shader_program, "projection")
        gl.glUniformMatrix4fv(model_loc, 1, gl.GL_TRUE, model)
        gl.glUniformMatrix4fv(view_loc, 1, gl.GL_TRUE, view)
        gl.glUniformMatrix4fv(proj_loc, 1, gl.GL_TRUE, projection)

        # Send ImGui parameters to shader
        gl.glUniform1f(gl.glGetUniformLocation(self.shader_program, "animationTime"), self.animation_time)
        gl.glUniform1f(gl.glGetUniformLocation(self.shader_program, "jiggleAmount"), self.jiggle_amount)
        gl.glUniform1f(gl.glGetUniformLocation(self.shader_program, "glowStrength"), self.glow_strength)
        gl.glUniform1f(gl.glGetUniformLocation(self.shader_program, "pulseIntensity"), self.pulse_intensity)

        # Send color and lighting
        gl.glUniform3f(gl.glGetUniformLocation(self.shader_program, "objectColor"), *color)
        gl.glUniform3f(gl.glGetUniformLocation(self.shader_program, "lightPos"), center_x, center_y - 100, 500.0)
        gl.glUniform3f(gl.glGetUniformLocation(self.shader_program, "viewPos"), center_x, center_y, 500.0)

        # Enable rendering - DISABLE face culling to ensure all faces render
        gl.glDisable(gl.GL_CULL_FACE)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glDisable(gl.GL_DEPTH_TEST)  # Disable depth test for 2D rendering

        # Now draw the sphere with shader
        gl.glUseProgram(self.shader_program)
        gl.glBindVertexArray(self.vao)
        if self.indices is not None:
            gl.glDrawElements(gl.GL_TRIANGLES, len(self.indices), gl.GL_UNSIGNED_INT, None)
            # Check for OpenGL errors
            err = gl.glGetError()
            if err != gl.GL_NO_ERROR:
                logger.error(f"OpenGL error after glDrawElements: {err}")
        else:
            gl.glDrawArrays(gl.GL_TRIANGLES, 0, len(self.vertices))
            err = gl.glGetError()
            if err != gl.GL_NO_ERROR:
                logger.error(f"OpenGL error after glDrawArrays: {err}")
        gl.glBindVertexArray(0)

        # Restore rendering states
        gl.glDisable(gl.GL_BLEND)

    def _setup_debug_quad(self):
        """Setup a debug quad for testing (placeholder)."""
        self._debug_quad_vao = True  # Just a flag

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
        logger.info("Energy sphere ImGui renderer cleaned up")
