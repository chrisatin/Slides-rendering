// Slide 03, pillar 1: a rendering engine follows light from a source to a
// surface and from there to the camera.
#import "/lib/slide_figure.typ": slide-figure, cetz
#import "/lib/diagram_parts.typ": palette, camera, ray, surface, light-source, normal-arrow
#show: slide-figure

#cetz.canvas({
  let hit = (1.6, 0)
  surface((0, 0), (3.2, 0), depth: 0.3, name: "floor")
  light-source((0.3, 1.7), aim: hit, name: "light")
  camera((3.0, 1.5), aim: hit, name: "cam")
  ray("light.front", hit, kind: "emission")
  ray(hit, "cam.lens", kind: "radiance")
  normal-arrow(hit, angle: 90deg, length: 0.8, label: none)
})
