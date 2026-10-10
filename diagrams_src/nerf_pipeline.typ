// Slide 05: how a NeRF is trained. Rays from the photos are sampled, an MLP
// turns each sample into colour and density, the volume integral composites
// them into a pixel, and the error against the photo trains the MLP.
#import "/lib/slide_figure.typ": slide-figure
#import "/lib/diagram_style.typ": flow, step, neural-step, edge, lbl
#import "/lib/diagram_parts.typ": palette
#show: slide-figure

#flow(
  spacing: (9mm, 10mm),
  step((0, 0), [fotos + poses \ de cámara], w: 26mm, name: <fotos>),
  step((1, 0), [un rayo \ por píxel], w: 22mm, name: <rayo>),
  step((2, 0), [muestras \ $(x, y, z, theta, phi)$], w: 30mm, name: <muestras>),
  neural-step((3, 0), [MLP $F_Theta$], w: 22mm, name: <mlp>, inset: 9pt),
  step((3, 1), [color y densidad \ $(bold(c), sigma)$], w: 30mm, name: <csigma>),
  step((2, 1), [integral de volumen], w: 30mm, name: <integral>),
  step((1, 1), [píxel \ renderizado], w: 22mm, name: <pixel>),
  neural-step((0, 1), [error contra \ la foto], w: 26mm, name: <loss>),

  edge(<fotos>, <rayo>, "-|>"),
  edge(<rayo>, <muestras>, "-|>"),
  edge(<muestras>, <mlp>, "-|>"),
  edge(<mlp>, <csigma>, "-|>"),
  edge(<csigma>, <integral>, "-|>"),
  edge(<integral>, <pixel>, "-|>"),
  edge(<pixel>, <loss>, "-|>"),
  edge(<loss>, (0, 1.75), (3.8, 1.75), (3.8, 0), <mlp>, "-|>", stroke: (paint: palette.neural, dash: "dashed"),
    label: lbl[gradiente: ajusta $Theta$], label-pos: 0.3, label-side: right),
)
