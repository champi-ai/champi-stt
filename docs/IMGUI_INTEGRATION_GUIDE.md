# Energy Sphere - ImGui Integration Guide

Complete guide for integrating the animated energy sphere into your ImGui C++ application.

## Table of Contents
1. [Quick Start](#quick-start)
2. [Loading the Model](#loading-the-model)
3. [Accessing Custom Properties](#accessing-custom-properties)
4. [ImGui Controls](#imgui-controls)
5. [Animation Loop](#animation-loop)
6. [Complete Example](#complete-example)
7. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Prerequisites
- ImGui installed and working
- 3D rendering library (OpenGL, DirectX, Vulkan)
- Model loading library (Assimp, TinyGLTF, or FBX SDK)

### Recommended Format
Use **Energy_Sphere.fbx** or **Energy_Sphere.glb** - both contain the custom properties.

---

## Loading the Model

### Option A: Using Assimp (FBX/GLB)

```cpp
#include <assimp/Importer.hpp>
#include <assimp/scene.h>
#include <assimp/postprocess.h>

class EnergySphere {
public:
    struct AnimationParams {
        float animationTime = 0.0f;
        float pulseSpeed = 1.0f;
        float pulseIntensity = 1.0f;
        float colorHue = 0.66f;        // Blue by default
        float colorSaturation = 1.0f;
        float glowStrength = 3.0f;
        float jiggleAmount = 0.0f;
    };

    AnimationParams params;

    bool Load(const std::string& filepath) {
        Assimp::Importer importer;
        const aiScene* scene = importer.ReadFile(filepath,
            aiProcess_Triangulate |
            aiProcess_GenNormals |
            aiProcess_CalcTangentSpace
        );

        if (!scene || scene->mFlags & AI_SCENE_FLAGS_INCOMPLETE || !scene->mRootNode) {
            std::cerr << "Assimp Error: " << importer.GetErrorString() << std::endl;
            return false;
        }

        LoadCustomProperties(scene);
        ProcessNode(scene->mRootNode, scene);

        return true;
    }

private:
    void LoadCustomProperties(const aiScene* scene) {
        if (scene->mMetaData) {
            aiMetadata* meta = scene->mMetaData;
            meta->Get("animation_time", params.animationTime);
            meta->Get("pulse_speed", params.pulseSpeed);
