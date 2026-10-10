// Slide 04: rasterization. Each vertex of the triangle is projected onto the
// image plane along its line towards the camera; the pixels between the
// projected vertices are the ones the triangle covers.
#import "/lib/slide_figure.typ": slide-figure, cetz
#import "/lib/diagram_parts.typ": palette, camera, ray, image-plane, note
#show: slide-figure

#cetz.canvas({
  import cetz.draw: line, circle
  let p = palette
  let eye = (0, 0.6)
  let plane-x = 1.5
  let plane-h = 2.8
  let n-px = 8
  let tri = ((4.3, 2.0), (5.3, 0.05), (3.8, -0.25))

  // Where the line from a vertex to the eye crosses the image plane.
  let proj(v) = {
    let t = (plane-x - eye.at(0)) / (v.at(0) - eye.at(0))
    (plane-x, eye.at(1) + t * (v.at(1) - eye.at(1)))
  }
  let ys = tri.map(v => proj(v).at(1))
  let top = eye.at(1) + plane-h / 2
  let h = plane-h / n-px
  let covered = range(n-px).filter(i => {
    let (y1, y0) = (top - i * h, top - (i + 1) * h)
    y0 < calc.max(..ys) and y1 > calc.min(..ys)
  })

  camera(eye, angle: 0deg, name: "cam", label: [cámara], label-side: "south")
  image-plane((plane-x, eye.at(1)), height: plane-h, pixels: n-px, highlight: covered, name: "plane")

  line(..tri, close: true, fill: p.blue-fill, stroke: 1pt + p.engines, name: "tri")
  for (i, v) in tri.enumerate() {
    ray(v, "cam.lens", kind: "missed", arrow: false)
    circle(v, radius: 0.07, fill: p.engines, stroke: none)
    circle(proj(v), radius: 0.05, fill: p.ink, stroke: none)
  }

  note("plane.top", [plano de imagen], offset: (0, 0.18), anchor: "south")
  note(tri.at(0), [vértices], offset: (0.18, 0.05), anchor: "west", fill: p.engines)
  note("plane.bottom", [píxeles que cubre: \ se pintan uno a uno], offset: (0.0, -0.18), anchor: "north")
  note(tri.at(1), [triángulo], offset: (0.1, -0.15), anchor: "north-west", fill: p.ink)
})
