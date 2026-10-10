# Implementation Plan: Rendering Research Line Pitch

**Objective:** Attract, engage, and recruit new students joining the research group by demonstrating the technical depth, visual impact, and future vision of the rendering line.
**Target Audience:** New research group students (undergraduate/graduate level).
**Estimated Duration:** 15-20 minutes (allowing ~1.5 minutes per slide + time for Q&A and demo videos).
**Language Rules:** The presentation delivery and all on-screen text must be in **Spanish**. Industry-standard technical terms (e.g., *NeRF, 3D Gaussian Splatting, Ray Tracing, Path Tracing, Neural Rendering*) must remain in **English**.

---

## 1. Visual Style & Aesthetic Guidelines

To capture the attention of technical students, the deck must look like a high-end SIGGRAPH or NVIDIA presentation. 

*   **Vibe:** "Cinematic Tech." High contrast, math-meets-art, cutting-edge.
*   **Palette:** 
    *   *Ground:* Deep dark background (e.g., `#0F172A` or pure black) to make renders and colors pop.
    *   *Accent:* Neon Blue or Magenta for UI elements, diagrams, and highlighted text.
    *   *Text:* High-contrast white and muted light grays.
*   **Typography:** A bold, geometric sans-serif for headings (e.g., *Space Grotesk* or *Syncopate*) and a highly readable sans-serif for body text (e.g., *Inter*), paired with a monospace font for technical terms and pseudo-code.
*   **Animations (HTML/CSS):** 
    *   Since HTML allows for dynamic elements, we will use subtle CSS keyframe animations.
    *   *Examples:* Pulsing nodes in neural network diagrams, glowing borders on current projects, fading-in text blocks to control the flow of information, and infinite scrolling data-lines to simulate computation.

---

## 2. Slide-by-Slide Breakdown

### Slide 1: The Hook (Title Slide)
*   **Topic:** Welcome & High-impact visual intro.
*   **Content:** Large title: "El Arte y la Matemática de la Luz" (The Art and Math of Light). Subtitle specifying the research line.
*   **Visual:** A full-bleed, hyper-realistic render or a looping background (placeholder for a NeRF fly-through).
*   **Goal:** Instantly grab attention. Show, don't just tell, what the end result of the research looks like.

### Slide 2: The "Why" (Para qué sirve el renderizado)
*   **Topic:** Real-world impact beyond just video games.
*   **Content:** Grid layout showing diverse applications. 
    *   *Simuladores para IA* (Autonomous driving).
    *   *Imágenes Médicas* (Volumetric scans).
    *   *Cine y VFX* (Photorealism).
    *   *Realidad Mixta* (XR/VR).
*   **Animation:** Sequential fade-in of the different application sectors.

### Slide 3: Our Core DNA (Líneas que trabajamos actualmente)
*   **Topic:** The three pillars of the current research group.
*   **Content:** A 3-column layout breaking down the core topics:
    1.  **Motores de Renderizado:** Building light physics from scratch (Ray Tracing, BRDFs).
    2.  **Volumetric Rendering:** Rendering clouds, smoke, and participating media (Ray Marching).
    3.  **Neural Rendering:** The intersection of Deep Learning and graphics.
*   **Visual:** Custom SVG icons for each pillar with a subtle hover or pulsing glow effect.

### Slide 4: Deep Dive - Motores de Renderizado
*   **Topic:** Unpacking the classic graphics pipeline.
*   **Content:** Brief explanation of how we simulate photons. Mentioning the heavy math involved (calculus, linear algebra, Monte Carlo integration).
*   **Visual:** A slick wireframe transitioning into a fully shaded 3D model, or a flowchart of a ray intersecting a scene.

### Slide 5: Deep Dive - Volumetric & Neural Rendering
*   **Topic:** How AI is changing graphics.
*   **Content:** Explaining the shift from explicit geometry (polygons) to implicit representations (neural networks).
*   **Vocabulary to highlight:** *NeRF (Neural Radiance Fields)*, *3D Gaussian Splatting*.
*   **Visual:** A diagram showing 2D images feeding into an MLP (Multi-Layer Perceptron) and outputting novel 3D views. Animated data flowing through the network nodes.

### Slide 6: Current Projects (Proyectos Actuales)
*   **Topic:** Proof of work. What are the students actually doing right now?
*   **Content:** 2 to 3 featured ongoing projects. Provide the project name, the main challenge, and the tech stack (e.g., C++, PyTorch, CUDA, OpenGL).
*   **Visual:** Split-screen or card layout showing screenshots or data visualizations from the students' actual research. 

### Slide 7: The Vision (Hacia dónde vamos)
*   **Topic:** The future strategy of the lab.
*   **Content:** The convergence of our two main strengths. We are focusing heavily on merging **Motores de Renderizado** (performance, explicit control) with **Neural Rendering** (AI-driven scene generation, *Gaussian Splatting*).
*   **Visual:** A bold timeline or roadmap graphic pointing towards a futuristic goal (e.g., "Real-time Neural Engines").

### Slide 8: The Pitch (Por qué unirte a nosotros)
*   **Topic:** Why this research line is the best choice for them.
*   **Content:** 3 main selling points:
    1.  *Matemática Aplicada:* You see your math come to life visually.
    2.  *Demanda en la Industria:* Top tech companies (NVIDIA, Epic Games, Apple) are desperate for these skills.
    3.  *Innovación:* You are working on the absolute frontier of computer science.
*   **Visual:** Big numbers and strong typography. 

### Slide 9: Join the Pipeline (Q&A and Call to Action)
*   **Topic:** Next steps.
*   **Content:** "Q&A", GitHub repo links, meeting times, and contact emails.
*   **Visual:** A clean, minimal layout with a large QR code pointing to the group's papers, repo, or sign-up form.

---

## 3. Execution Notes for the Speaker
*   **Timing:** Keep slides 2-5 brief. The focus should be on slides 6, 7, and 8—students want to know what they will be doing, where the lab is going, and how it benefits their careers.
*   **Demos:** When presenting, if you have actual videos of a *NeRF* or *Gaussian Splat* trained by the lab, replace the static images in the HTML presentation with local `.mp4` files. There is nothing more convincing than a live visual result.
