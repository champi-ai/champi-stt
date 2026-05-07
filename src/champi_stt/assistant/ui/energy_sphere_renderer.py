"""3D Energy Sphere renderer for wake indicator UI.

Renders a 3D energy sphere model using OpenGL, with audio-responsive effects.
"""

import math
from pathlib import Path

import numpy as np
import OpenGL.GL as gl  # noqa: N811
from loguru import logger


class EnergySphereRenderer:
    """Renders 3D energy sphere with audio-responsive effects."""

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

        # Get path to energy sphere model
        # Go up to src/champi_stt/assistant/ui -> src/champi_stt -> src -> assets
        self.assets_dir = (
            Path(__file__).parent.parent.parent.parent / "assets" / "energy_sphere"
        )
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

                # Extract mesh data from GLTF
                self._extract_gltf_data(gltf)
                self.model_loaded = True
                return True

            except ImportError:
                logger.warning("pygltflib not available, falling back to simple sphere")
                # Create a simple sphere mesh as fallback
                self._create_fallback_sphere()
                self.model_loaded = True
                self._fallback_mode = True
                return False

        except Exception as e:
            logger.error(f"Failed to load energy sphere: {e}")
            # Create fallback sphere
            self._create_fallback_sphere()
            self.model_loaded = True
            self._fallback_mode = True
            return False

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
        normal_accessor_idx = (
            primitive.attributes.NORMAL
            if hasattr(primitive.attributes, "NORMAL")
            else None
        )
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
        """Create vertex and fragment shaders."""
        # Vertex shader
        vertex_shader_source = """
        #version 330 core
        layout (location = 0) in vec3 aPos;
        layout (location = 1) in vec3 aNormal;

        uniform mat4 model;
        uniform mat4 view;
        uniform mat4 projection;

        out vec3 FragPos;
        out vec3 Normal;

        void main()
        {
            FragPos = vec3(model * vec4(aPos, 1.0));
            Normal = mat3(transpose(inverse(model))) * aNormal;
            gl_Position = projection * view * vec4(FragPos, 1.0);
        }
        """

        # Fragment shader
        fragment_shader_source = """
        #version 330 core
        out vec4 FragColor;

        in vec3 FragPos;
        in vec3 Normal;

        uniform vec3 lightPos;
        uniform vec3 viewPos;
        uniform vec3 objectColor;
        uniform float glowStrength;

        void main()
        {
            // Ambient
            float ambientStrength = 0.3;
            vec3 ambient = ambientStrength * objectColor;

            // Diffuse
            vec3 norm = normalize(Normal);
            vec3 lightDir = normalize(lightPos - FragPos);
            float diff = max(dot(norm, lightDir), 0.0);
            vec3 diffuse = diff * objectColor;

            // Specular (for glow effect)
            float specularStrength = 0.8;
            vec3 viewDir = normalize(viewPos - FragPos);
            vec3 reflectDir = reflect(-lightDir, norm);
            float spec = pow(max(dot(viewDir, reflectDir), 0.0), 32);
            vec3 specular = specularStrength * spec * objectColor;

            // Fresnel glow effect
            float fresnel = pow(1.0 - max(dot(viewDir, norm), 0.0), 3.0);
            vec3 glow = fresnel * glowStrength * objectColor;

            // Boost brightness for better visibility
            vec3 result = (ambient + diffuse + specular + glow) * 1.5;
            FragColor = vec4(result, 1.0);  // Fully opaque
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
        color: tuple[float, float, float] = (0.2, 0.8, 0.2),
    ):
        """Render the energy sphere.

        Args:
            center_x: Center X position in screen coordinates
            center_y: Center Y position in screen coordinates
            radius: Base radius
            window_width: Window width
            window_height: Window height
            audio_intensity: Audio intensity for pulsing (0-1)
            x_squeeze: X-axis squeeze factor
            y_squeeze: Y-axis squeeze factor
            color: RGB color tuple (0-1 range)
        """

        if not self.model_loaded or self.shader_program is None:
            logger.warning(
                "Skipping render - model not loaded or shader program missing"
            )
            return

        try:
            # Use shader program
            gl.glUseProgram(self.shader_program)

            # Set up model matrix (scale, translate)
            model = np.eye(4, dtype=np.float32)

            # Scale based on radius and audio
            scale = radius * (1.0 + audio_intensity * 0.3)
            model[0, 0] = scale * x_squeeze
            model[1, 1] = scale * y_squeeze
            model[2, 2] = scale

            # Translate to screen position (in 3D space)
            model[3, 0] = center_x
            model[3, 1] = center_y
            model[3, 2] = 0.0

            # Identity view matrix (no camera transformation)
            view = np.eye(4, dtype=np.float32)

            # Orthographic projection for 2D screen space
            # Convert screen coordinates to normalized device coordinates (-1 to 1)
            left = 0.0
            right = float(window_width)
            bottom = float(window_height)
            top = 0.0
            near = -1000.0  # Large range to include our sphere at z=0
            far = 1000.0

            # Build orthographic projection matrix
            projection = np.zeros((4, 4), dtype=np.float32)
            projection[0, 0] = 2.0 / (right - left)
            projection[1, 1] = 2.0 / (top - bottom)
            projection[2, 2] = -2.0 / (far - near)
            projection[3, 3] = 1.0
            projection[0, 3] = -(right + left) / (right - left)
            projection[1, 3] = -(top + bottom) / (top - bottom)
            projection[2, 3] = -(far + near) / (far - near)

        except Exception as e:
            logger.error(f"Error in render setup: {e}")
            import traceback

            logger.error(traceback.format_exc())
            raise

        # Send matrices to shader
        model_loc = gl.glGetUniformLocation(self.shader_program, "model")
        view_loc = gl.glGetUniformLocation(self.shader_program, "view")
        proj_loc = gl.glGetUniformLocation(self.shader_program, "projection")

        # Transpose matrices for OpenGL (column-major)
        gl.glUniformMatrix4fv(model_loc, 1, gl.GL_TRUE, model)
        gl.glUniformMatrix4fv(view_loc, 1, gl.GL_TRUE, view)
        gl.glUniformMatrix4fv(proj_loc, 1, gl.GL_TRUE, projection)

        # Set color and lighting uniforms
        color_loc = gl.glGetUniformLocation(self.shader_program, "objectColor")
        gl.glUniform3f(color_loc, *color)

        # Light position: above and in front of sphere in screen space
        light_pos_loc = gl.glGetUniformLocation(self.shader_program, "lightPos")
        gl.glUniform3f(light_pos_loc, center_x, center_y - 100, 500.0)

        # View position: camera looking at sphere from front
        view_pos_loc = gl.glGetUniformLocation(self.shader_program, "viewPos")
        gl.glUniform3f(view_pos_loc, center_x, center_y, 500.0)

        glow_loc = gl.glGetUniformLocation(self.shader_program, "glowStrength")
        gl.glUniform1f(glow_loc, 1.0 + audio_intensity * 2.0)

        # Enable blending for transparency
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

        # Enable depth testing
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
