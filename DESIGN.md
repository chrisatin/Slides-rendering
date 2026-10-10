# Design System: Rendering Research Line Pitch

Este documento define las directrices visuales, paleta de colores, tipografía y animaciones para la presentación interactiva del grupo de investigación de renderizado. El objetivo es mantener una estética "Cinematic Tech" coherente, profesional y altamente atractiva para perfiles técnicos.

## 1. Filosofía Visual (Cinematic Tech)
* **Contraste Extremo:** Fondos muy oscuros para que los renders fotorealistas y los diagramas brillen.
* **Minimalismo Matemático:** UI limpia, líneas finas y un enfoque en el contenido visual (imágenes, código, fórmulas matemáticas).
* **Dinámismo Técnico:** Animaciones sutiles que simulen procesamiento de datos y cálculo computacional.

## 2. Paleta de Colores

### Fondos y Superficies (Dark Mode)
* `Background Base`: **#0B0F19** (Azul noche casi negro) - Fondo principal de todas las diapositivas.
* `Surface / Cards`: **#151E2E** (Gris azulado oscuro) - Para tarjetas, contenedores de proyectos y diagramas.
* `Borders / Dividers`: **#334155** (Gris pizarra) - Líneas sutiles de separación.

### Texto
* `Text Primary`: **#F8FAFC** (Blanco brillante) - Títulos y datos clave.
* `Text Secondary`: **#94A3B8** (Gris claro) - Párrafos y descripciones largas.
* `Text Code`: **#38BDF8** (Cian) - Para términos técnicos en inglés (e.g., *NeRF*, *Ray Tracing*).

### Acentos (Neon Glow)
* `Accent Primary`: **#6366F1** (Indigo) - Botones principales, íconos de la línea de motores.
* `Accent Secondary`: **#EC4899** (Rosa neón) - Íconos de la línea de Neural Rendering y llamadas a la acción (CTAs).
* `Accent Glow`: Se utilizarán sombras difuminadas (`box-shadow`) usando los colores de acento con baja opacidad (ej. `rgba(99, 102, 241, 0.3)`) para simular emisión de luz.

## 3. Tipografía

El sistema utilizará fuentes de Google Fonts para garantizar compatibilidad web:

* **Títulos (Headings):** `Space Grotesk`
  * *Pesos:* 700 (Bold) para títulos de slides, 500 (Medium) para subtítulos.
  * *Estilo:* Geométrica y futurista. Da un aspecto de "computación de vanguardia".
* **Cuerpo de Texto (Body):** `Inter`
  * *Pesos:* 400 (Regular) para párrafos, 500 (Medium) para listas.
  * *Estilo:* Altamente legible, limpia, estándar en interfaces modernas.
* **Términos Técnicos / Código:** `Fira Code` (o `Roboto Mono`)
  * *Pesos:* 400 (Regular).
  * *Uso:* Exclusivo para nombres de algoritmos, papers, o pseudo-código.

## 4. Estructura y Espaciado (Grid System)

* **Contenedor Principal:** `1280px` por `720px` (Aspect Ratio 16:9 estricto para pantallas).
* **Padding (Márgenes internos):**
  * Bordes de la pantalla: `64px` o `80px`.
  * Entre secciones internas (ej. título y columnas): `40px`.
  * Entre elementos de lista: `16px`.
* **Border Radius:**
  * Tarjetas e imágenes: `12px` (Bordes ligeramente redondeados, pero manteniendo un aspecto estructural).

## 5. Animaciones CSS (Motion UI)

Las animaciones deben ser fluidas y técnicas, nunca exageradas. Todo se manejará a través de transiciones CSS y `@keyframes`.

1. **Fade-In Up:**
   * *Uso:* Para la entrada de elementos de texto y listas.
   * *Curva:* `cubic-bezier(0.4, 0, 0.2, 1)`
   * *Duración:* `0.6s`
2. **Pulsing Glow:**
   * *Uso:* Para nodos en los diagramas de redes neuronales (Neural Rendering) o para destacar líneas de código activas.
   * *Efecto:* Animación en bucle alternando el brillo de la sombra (box-shadow).
3. **Data Flow (Líneas de datos):**
   * *Uso:* Para las diapositivas de *Deep Dive*.
   * *Efecto:* Fondos con patrones de cuadrícula que se desplazan lentamente o líneas divisorias que cambian de gradiente imitando el paso de información.

## 6. Iconografía y Recursos

* **Íconos:** Biblioteca FontAwesome (estilo sólido y regular).
* **Imágenes:** Se priorizará el uso de *placeholders* oscuros o capturas reales de renders generados por el grupo. Los videos en bucle (`.mp4` sin sonido) de escenas generadas por *Gaussian Splatting* se colocarán como fondos de bajo contraste para la portada.