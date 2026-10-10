# Notas del orador: El Arte y la Matemática de la Luz

Charla de reclutamiento de la línea de renderizado del Semillero Hands-on Computer Vision.
Duración prevista: 15 a 18 minutos más preguntas. Las diapositivas 2 a 5 van rápido; el peso está en la 6, la 7 y la 8, que responden lo que el público quiere saber: qué haría, hacia dónde va el grupo y qué gana.

Convenciones de este documento:

- **[clic]** marca un avance que revela un elemento de la diapositiva (los fragmentos de Reveal).
- Los términos técnicos se dicen en inglés, como aparecen en pantalla (*Ray Tracing*, *NeRF*, *3D Gaussian Splatting*).
- Las notas dentro de `index.html` (tecla **S** en la presentación) son una versión corta de estas.

| # | Diapositiva | Tiempo | Clics |
|---|---|---|---|
| 1 | Portada | 1 min | 0 |
| 2 | El renderizado no es solo para videojuegos | 1,5 min | 4 |
| 3 | Tres formas de calcular la luz | 1,5 min | 3 |
| 4 | ¿Cómo se simula un fotón? | 2 min | 3 |
| 5 | De polígonos a redes neuronales | 2,5 min | 6 |
| 6 | Lo que estamos construyendo | 3 min | 3 |
| 7 | Hacia dónde vamos | 2 min | 3 |
| 8 | Por qué unirte | 2 min | 3 |
| 9 | ¿Preguntas? | resto | 0 |

---

## 1. Portada: El Arte y la Matemática de la Luz

**Mensaje:** lo que ven en pantalla no es una foto; es matemática resuelta por un computador.

**Qué decir:**

Esta imagen no es una foto. La renderizamos nosotros con Mitsuba 3, el renderizador físico con el que trabaja el semillero. Un haz de luz atraviesa una niebla tenue, entra a una esfera de vidrio, se refracta y forma una cáustica en el piso; al lado hay una esfera de oro rugoso. Nada de eso se dibujó a mano: todo sale de simular cómo viaja la luz.

Hoy les cuento qué hacemos en la línea de renderizado, en qué están trabajando los estudiantes ahora mismo y por qué vale la pena unirse.

**Transición:** "Antes de entrar en la matemática, ¿para qué sirve todo esto fuera de los videojuegos?"

**Si preguntan:**

- *¿Cuánto tardó?* Unos 47 minutos en una GPU de portátil (RTX 3050), con 640 muestras por píxel.
- *¿Por qué se ve un haz?* La niebla dispersa la luz; sin un medio participativo el haz sería invisible. Es la línea de *Volumetric Rendering* que veremos en un momento.

---

## 2. El renderizado no es solo para videojuegos

**Mensaje:** cualquier máquina que necesite ver un mundo que no existe depende del renderizado.

**Qué decir:**

**[clic]** Simuladores para IA: los autos autónomos también se entrenan con imágenes sintéticas, escenas que nunca existieron pero que se ven y se comportan como la calle.

**[clic]** Imágenes médicas: una tomografía es un volumen de datos. Para verla como un cráneo hay que renderizarla, con la misma familia de técnicas que usamos para el humo y las nubes.

**[clic]** Cine y VFX: los personajes y mundos digitales que ven en pantalla son render.

**[clic]** Realidad mixta: si un objeto virtual no se ilumina como el cuarto en el que estás, el cerebro lo detecta de inmediato como falso.

**Transición:** "Para atacar estos problemas, en el semillero trabajamos en tres frentes."

**Nota:** las imágenes son de cursos de neural rendering de Penn y TUM, no del grupo. Si alguien pregunta, decirlo.

---

## 3. Tres formas de calcular la luz

**Mensaje:** el grupo trabaja tres líneas, y dos de ellas comparten la misma matemática.

**Qué decir:**

**[clic]** Motores de Renderizado: escribimos la física de la luz desde cero. Rayos que salen de una fuente, rebotan en un material y llegan a la cámara. Aquí viven *Ray Tracing*, *Path Tracing* y las BRDF, que describen cómo refleja cada material.

**[clic]** *Volumetric Rendering*: cuando la luz no rebota en una superficie sino que se dispersa dentro de un medio, como una nube, el humo o el aire. El dibujo muestra un camino que se dispersa varias veces antes de salir.

**[clic]** *Neural Rendering*: redes neuronales que aprenden una escena 3D a partir de fotos. *NeRF* y *3D Gaussian Splatting*.

Quédense con una idea: la segunda y la tercera usan la misma integral. Lo van a ver en dos diapositivas.

**Transición:** "Empecemos por la base: ¿cómo se simula un fotón?"

---

## 4. ¿Cómo se simula un fotón?

**Mensaje:** hay dos estrategias para colorear un píxel, y las dos aproximan la misma ecuación.

**Qué decir:**

**[clic]** *Rasterization* va del objeto al píxel. Toma los vértices de cada triángulo, los proyecta sobre el plano de imagen y pinta los píxeles que el triángulo cubre. Es muy rápido; es lo que hace la GPU en un videojuego.

**[clic]** *Ray Tracing* va al revés: del píxel a la escena. Desde la cámara sale un rayo por cada píxel; cuando choca con la esfera, el programa hace dos preguntas más. ¿La luz es visible desde aquí? Eso es el rayo de sombra. ¿Qué se ve en el reflejo? Eso es el rayo reflejado. Por eso las sombras y los reflejos salen físicamente correctos.

**[clic]** Las dos aproximan la ecuación de renderizado de Kajiya: la luz que sale de un punto es la que emite, más la integral de toda la luz que llega, multiplicada por el material y por el coseno del ángulo. Esa integral no tiene forma cerrada; la estimamos con integración Monte Carlo, promediando caminos aleatorios. Aquí se cruzan cálculo, álgebra lineal y probabilidad.

**Transición:** "Esa misma idea, integrar a lo largo de un rayo, es la puerta hacia las redes neuronales."

**Si preguntan:**

- *¿Por qué hay ruido en los renders?* Monte Carlo es un promedio de muestras aleatorias; el error baja como 1/√N, así que para reducir el ruido a la mitad hacen falta cuatro veces más muestras.

---

## 5. De polígonos a redes neuronales

**Mensaje:** la integral que renderiza una nube es la misma que entrena una *NeRF*.

**Qué decir:**

**[clic]** Explícito: en gráficos clásicos alguien modela la escena con triángulos, vértice por vértice.

**[clic]** Implícito: en *Neural Rendering* la escena es una función. Una red recibe un punto del espacio y una dirección, y devuelve un color y una densidad.

**[clic]** ¿Cómo se convierte eso en una imagen? Con la integral de volumen: a lo largo del rayo se acumula el color de cada punto, pesado por su densidad y por cuánta luz sobrevive hasta la cámara, que es la transmitancia T. Es exactamente la ecuación que usamos para renderizar nubes y humo.

**[clic]** *3D Gaussian Splatting* llega a un resultado parecido sin red: representa la escena con una nube de gaussianas 3D que se rasterizan en tiempo real.

**[clic]** El ciclo de entrenamiento de una *NeRF*: fotos con sus poses de cámara, un rayo por píxel, muestras a lo largo del rayo, la red, color y densidad, la integral de volumen y un píxel renderizado. Ese píxel se compara con la foto, y el error ajusta la red por gradiente.

**[clic]** El resultado: vistas nuevas de la escena, desde posiciones donde nunca hubo una cámara.

**Transición:** "Con esa base, veamos qué están construyendo los estudiantes del semillero."

---

## 6. Lo que estamos construyendo

**Mensaje:** los proyectos actuales trabajan con luz que el ojo no ve, y todos están en desarrollo.

**Qué decir:**

Son tres proyectos de grado, todos en curso, y todos con luz fuera del espectro visible: el infrarrojo térmico y las imágenes hiperespectrales.

**[clic]** Jorge construye un simulador de imágenes en infrarrojo de onda larga. Resuelve la ecuación de transferencia radiativa con *Volumetric Rendering*, sobre Mitsuba 3. El video es un render de su simulador:

- Cinco esferas de materiales medidos de la biblioteca ECOSTRESS: pasto a 25 °C, concreto a 35 °C, techo de aluminio a 40 °C, ladrillo a 45 °C y asfalto a 50 °C. Están sobre un suelo medido a 30 °C, dentro de aire a 20 °C y bajo un cielo a −20 °C.
- La cámara da una vuelta completa mientras la banda va de 8 a 10 micras y regresa. El color es temperatura de brillo, en una sola escala de −20 °C a 50 °C.
- Señalar la esfera de aluminio: está a 40 °C y sin embargo se ve fría. El aluminio refleja cerca del 95 % en este rango, así que casi no emite y lo que la cámara ve es el reflejo del cielo frío. Una cámara térmica real cometería el mismo "error", y el simulador lo reproduce.
- Fíjense también en el cielo: cerca de 8 micras se ve más cálido, porque el vapor de agua del aire emite ahí; entre 9 y 10 micras el aire es más transparente y el cielo se ve oscuro.

**[clic]** Chris Orduz sintetiza vistas nuevas en infrarrojo de onda larga con *3D Gaussian Splatting* guiado por la física.

**[clic]** Juanda hace *3D Gaussian Splatting* sobre imágenes hiperespectrales, usando desmezclado espectral (*spectral unmixing*) para separar los materiales de cada píxel.

**Transición:** "Estos proyectos muestran las dos fortalezas del grupo. La pregunta es qué pasa cuando las juntamos."

**Si preguntan:**

- *¿Qué es temperatura de brillo?* La temperatura que tendría un cuerpo negro para emitir la radiancia que mide la cámara. Coincide con la temperatura real solo si el material emite como un cuerpo negro; por eso el aluminio "miente".
- *¿Cuánto tardó el video?* 360 cuadros a 800 × 400 en la GPU del clúster de CVAIL (RTX PRO 6000), unos 45 minutos. Cada cuadro promedia 32 longitudes de onda dentro de una banda de 200 nm para que las líneas de absorción del aire no parpadeen.

**Pendiente antes de presentar:** el stack de cada proyecto (los recuadros punteados en pantalla). El proyecto de Juan Toloza se menciona en la diapositiva 7.

---

## 7. Hacia dónde vamos

**Mensaje:** hacia el futuro, la idea es explorar tres áreas: renderizado, *Inverse Rendering* y *Neural Rendering*.

**Qué decir:**

Al entrar a la diapositiva, los tres rayos se dibujan solos y se juntan en un solo haz:

- Arriba, el renderizado: conocemos la escena (geometría, materiales, luces) y simulamos la imagen. Es lo que hacen los motores físicos y nos da control y exactitud.
- En el medio, el *Inverse Rendering*: el camino contrario. Partimos de fotos y recuperamos la escena: geometría, materiales e iluminación.
- Abajo, el *Neural Rendering*: redes que aprenden la escena a partir de fotos y la renderizan rápido.

**[clic]** Hoy: tenemos simuladores físicos, Mitsuba 3 con la ecuación de transferencia radiativa, y *3D Gaussian Splatting* espectral, cada uno por su lado.

**[clic]** Siguiente: el proyecto de Juan Toloza se va a extender para seguir incorporando simuladores.

**[clic]** Meta: trabajar las tres áreas juntas: simular, recuperar la escena desde fotos y aprenderla con redes.

**Transición:** "¿Y qué gana usted si se une a esto?"

**Pendiente antes de presentar:** decidir si se menciona el grant de NVIDIA y en qué estado está. Hoy no aparece en pantalla.

---

## 8. Por qué unirte

**Mensaje:** matemática que se ve, habilidades que la industria pide y resultados reales.

**Qué decir:**

Empezar por los dos resultados de la izquierda:

- Arriba: este año el semillero quedó en tercer puesto en el reto de *novel view synthesis* del workshop CVsports, en CVPR 2026, en Denver. La imagen es una vista sintetizada de un partido de fútbol, el tipo de escena del reto.
- Abajo: segundo puesto en semilleros con «De 2D a gemelos digitales: creación automática de entornos 3D con IA». El video recorre su flujo de trabajo: imagen satelital del campus, segmentación con SAM 3, árboles generados, edificios con BlenderGIS y la escena 3D final. En el equipo estaban Jorge García y Christian Orduz, de esta línea, junto con Giojan David, Mandius Fonseca, Santiago Amaya y Santiago Salamanca.
- El enlace «Ver el modelo 3D» abre el modelo en el navegador; se puede usar en vivo si hay conexión.

**[clic]** Matemática que se ve: cálculo, álgebra lineal y probabilidad con resultado en pantalla. Si la integral está mal, el píxel también, y se nota.

**[clic]** Habilidades que pide la industria: C++, CUDA, PyTorch y renderizado físico. Es lo que buscan los equipos de gráficos de empresas como NVIDIA, Epic Games o Apple.

**[clic]** Investigación de frontera: trabajamos con métodos publicados el último año y competimos en retos de CVPR y en semilleros.

**Transición:** "Eso es lo que hacemos. Ahora, sus preguntas."

**Cuidado:** no presentar como dato que esas empresas "contratan a nuestros estudiantes"; en pantalla solo se dice que buscan esas habilidades.

**Si preguntan:** el código del proyecto de semilleros está en github.com/Manmanfr/UIS-Render.

**Pendiente antes de presentar:** nombre del evento de semilleros y año (recuadro punteado en pantalla).

---

## 9. ¿Preguntas?

**Mensaje:** si alguna línea les interesó, hay un paso concreto para entrar.

**Qué decir:**

Ahora sí, preguntas. Y si alguna de las tres líneas les llamó la atención, escríbannos o escaneen el QR: los invitamos a la próxima reunión del semillero.

**Pendiente antes de presentar:** correo de contacto, día y hora de las reuniones, enlace al repositorio y el enlace del QR. Hoy están como recuadros punteados.

**Preguntas probables:**

- *¿Qué lenguajes se usan?* Mitsuba 3 está en C++ con interfaz de Python, y la parte neuronal usa PyTorch.
- *¿Qué necesito saber para entrar?* [Confirmar con el grupo antes de responder.]
- *¿Necesito una GPU propia?* [Confirmar si los nuevos integrantes tienen acceso al clúster.]

---

## Lista de pendientes

- [ ] Stack de cada proyecto (diapositiva 6; `info/*.yml`).
- [ ] Estado del grant de NVIDIA y si se menciona (diapositiva 7).
- [ ] Nombre del evento de semilleros y año (diapositiva 8).
- [ ] Correo, horario de reuniones, repositorio y enlace del QR (diapositiva 9).
