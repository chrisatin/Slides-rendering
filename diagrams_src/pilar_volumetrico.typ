// Slide 03, pillar 2: inside a participating medium (cloud, smoke) a path
// scatters several times before it leaves.
#import "/lib/slide_figure.typ": slide-figure, cetz
#import "/lib/diagram_parts.typ": palette, ray, medium, event
#show: slide-figure

#cetz.canvas({
  let path = ((-0.5, 0.9), (0.7, 0.75), (1.3, 1.45), (2.05, 0.55), (2.5, 1.2), (3.6, 1.4))
  medium((0, 0), (3.0, 2.0), boundary: "dashed", radius: 0.25, name: "nube")
  for i in range(path.len() - 1) {
    ray(path.at(i), path.at(i + 1), kind: if i == 0 { "emission" } else { "radiance" })
  }
  for v in path.slice(1, -1) { event(v, kind: "scatter") }
})
