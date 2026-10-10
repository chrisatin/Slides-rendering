// One style for every flowchart of the presentation, drawn with fletcher (on
// CeTZ), so that nodes can hold math and code: surface-coloured steps outlined
// in the colour of their research line, cyan hexagonal decisions, dashed notes
// and italic edge labels, in the palette of lib/diagram_parts.typ.
#import "@preview/fletcher:0.5.8" as fletcher: diagram, node
#import "/lib/diagram_parts.typ": palette

// An edge whose label sits 70 % of the way along it, away from the source
// node, and well clear of the line. Any argument given at the call site overrides this default.
#let edge(..args) = fletcher.edge(..args.pos(), ..((label-pos: 0.7, label-sep: 0.7em) + args.named()))

#let _body(body, w) = box(width: w, align(center, par(justify: false, leading: 0.45em, body)))

// A step of the flow; its text wraps at the width `w`. Every style argument
// given at the call site overrides the default.
#let _node(pos, body, w, defaults, args) = node(pos, _body(body, w), ..args.pos(), ..(defaults + args.named()))

// A step of the rendering-engines line (ray tracing, BRDFs, Monte Carlo).
#let step(pos, body, w: 40mm, ..args) = _node(pos, body, w,
  (fill: palette.slab, stroke: 0.8pt + palette.engines, corner-radius: 3pt, inset: 6pt), args)

// A step of the Neural Rendering line (NeRF, 3D Gaussian Splatting, MLPs).
#let neural-step(pos, body, w: 40mm, ..args) = _node(pos, body, w,
  (fill: palette.slab, stroke: 0.8pt + palette.neural, corner-radius: 3pt, inset: 6pt), args)

// A decision, drawn as a hexagon.
#let decision(pos, body, w: 34mm, ..args) = _node(pos, body, w,
  (fill: palette.warm-fill, stroke: 0.8pt + palette.warm, shape: fletcher.shapes.hexagon, inset: 5pt), args)

// A side note, attached to a step by a dashed edge.
#let note(pos, body, w: 34mm, ..args) = _node(pos, body, w,
  (fill: none, stroke: (paint: palette.ink2, thickness: 0.6pt, dash: "dashed"), corner-radius: 3pt, inset: 5pt), args)

// The hollow arrowhead of inheritance.
#let inherits = (inherit: "stealth", stealth: 0, size: 9, fill: palette.bg)

// An edge label, in italics.
#let lbl(body) = text(style: "italic", fill: palette.ink2, body)

// The diagram itself, in the arrows and spacing of the deck.
#let flow(..args) = diagram(spacing: (10mm, 12mm), edge-stroke: 0.8pt + palette.ink2,
  mark-scale: 80%, label-size: 9pt, ..args)
