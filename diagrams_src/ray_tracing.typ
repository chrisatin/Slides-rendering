// Slide 04: ray tracing. A primary ray leaves the camera through one pixel,
// hits the sphere, and from the hit point the renderer asks two more
// questions: is the light visible (shadow ray) and what does the reflection
// see (reflected ray).
#import "/lib/slide_figure.typ": slide-figure, cetz
#import "/lib/diagram_parts.typ": palette, camera, ray, image-plane, light-source, surface, normal-arrow, on-boundary, note
#show: slide-figure

#cetz.canvas({
  import cetz.draw: circle
  let p = palette
  let eye = (0, 0.6)
  let plane-x = 1.5
  let ball = (4.6, 0.55)
  let r = 0.85
  let hit-angle = 165deg
  let hit = on-boundary(ball, r, hit-angle)

  // Mirror direction of the primary ray about the normal at the hit point.
  let d = (hit.at(0) - eye.at(0), hit.at(1) - eye.at(1))
  let dn = calc.sqrt(d.at(0) * d.at(0) + d.at(1) * d.at(1))
  let d = (d.at(0) / dn, d.at(1) / dn)
  let n = (calc.cos(hit-angle), calc.sin(hit-angle))
  let k = 2 * (d.at(0) * n.at(0) + d.at(1) * n.at(1))
  let refl = (d.at(0) - k * n.at(0), d.at(1) - k * n.at(1))
  let refl-end = (hit.at(0) + 1.7 * refl.at(0), hit.at(1) + 1.7 * refl.at(1))

  surface((-0.4, -0.45), (6.0, -0.45), depth: 0.25, name: "floor")
  camera(eye, angle: 0deg, name: "cam", label: [cámara], label-side: "south")
  image-plane((plane-x, eye.at(1)), height: 2.8, pixels: 8, highlight: (3,), name: "plane")
  circle(ball, radius: r, fill: p.slab, stroke: 1pt + p.ink2, name: "ball")
  light-source((5.2, 2.75), aim: hit, name: "light", label: none)

  ray("cam.lens", hit, kind: "radiance", label: [rayo primario], label-side: "right",
    label-pos: 0.72, label-dist: 0.2, label-anchor: "north")
  ray(hit, "light.center", kind: "shadow", label: [rayo de sombra], label-side: "right",
    label-pos: 0.45, label-dist: 0.2, label-anchor: "west")
  ray(hit, refl-end, kind: "reflected", label: [reflexión], label-side: "right",
    label-pos: 0.9, label-dist: 0.2, label-anchor: "south")
  normal-arrow(hit, angle: hit-angle, length: 0.55, label: none)
  circle(hit, radius: 0.06, fill: p.ink, stroke: none)

  note("plane.top", [un píxel], offset: (0, 0.18), anchor: "south")
  note("light.center", [luz], offset: (0.3, 0.0), anchor: "west", fill: p.warm)
  note(ball, [esfera], fill: p.ink)
})
