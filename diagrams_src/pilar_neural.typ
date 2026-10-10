// Slide 03, pillar 3: a small MLP, the network behind NeRF, from a 3D
// position and direction to colour and density.
#import "/lib/slide_figure.typ": slide-figure, cetz
#import "/lib/diagram_parts.typ": palette, note
#show: slide-figure

#cetz.canvas({
  import cetz.draw: circle, line
  let p = palette
  let layers = (3, 4, 4, 2)
  let pos(l, i) = (l * 1.0, (i - (layers.at(l) - 1) / 2) * 0.55)
  for l in range(layers.len() - 1) {
    for i in range(layers.at(l)) {
      for j in range(layers.at(l + 1)) {
        line(pos(l, i), pos(l + 1, j), stroke: 0.4pt + p.ink2.transparentize(40%))
      }
    }
  }
  for l in range(layers.len()) {
    for i in range(layers.at(l)) {
      circle(pos(l, i), radius: 0.13, fill: p.slab, stroke: 0.9pt + p.neural)
    }
  }
  note(pos(0, 1), $bold(x), bold(d)$, offset: (-0.25, 0), anchor: "east", fill: p.ink)
  note((3.0, 0), $bold(c), sigma$, offset: (0.25, 0), anchor: "west", fill: p.ink)
})
