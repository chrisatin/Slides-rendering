#import "@preview/cetz:0.5.2"

// Parts shared by the CeTZ drawings of the presentation, so that a camera, a
// path event or a surface normal looks the same on every slide. Each part is
// a function that emits draw commands and is called inside a cetz.canvas.

// DESIGN.md tokens for dark slides. `warm` keeps its role (light, rays,
// emitters) but is the cyan of the deck; `blue` (other quantities) is the
// engines indigo, lightened to stay above 3:1 on the slide background.
#let palette = (
  warm: rgb("#38BDF8"),
  warm-fill: rgb("#38BDF8").transparentize(82%),
  blue: rgb("#818CF8"),
  blue-fill: rgb("#6366F1").transparentize(80%),
  engines: rgb("#818CF8"),
  neural: rgb("#EC4899"),
  neural-fill: rgb("#EC4899").transparentize(82%),
  ink: rgb("#F8FAFC"),
  ink2: rgb("#94A3B8"),
  neutral: rgb("#94A3B8"),
  slab: rgb("#151E2E"),
  body: rgb("#334155"),
  bg: rgb("#0B0F19"),
  // Categorical slots for several unordered groups in one drawing, in this fixed
  // order (the chart palette of tools/figures/make_figures.py).
  cat: ("#6366F1", "#EC4899", "#0C9EE2", "#EA580C", "#059669", "#EF4444", "#0D9488", "#D97706").map(rgb),
)

// A camera: a body and a lens hood that opens towards the scene. `pos` is the
// front of the lens, where rays start, a point or an anchor; `angle` is the
// viewing direction (0deg looks along +x), or the camera looks at the point
// `aim` if one is given; `size` scales the icon. The group exposes the anchors
// "<name>.lens" (the front of the lens) and "<name>.body".
#let camera(pos, angle: 0deg, aim: none, size: 1, name: "cam", label: none, label-side: "south") = {
  import cetz.draw: *
  let p = palette
  get-ctx(ctx => {
    let (_, cv) = cetz.coordinate.resolve(ctx, pos)
    let c = (cv.at(0), cv.at(1))
    let angle = if aim == none { angle } else {
      let (_, t) = cetz.coordinate.resolve(ctx, aim)
      calc.atan2(t.at(0) - c.at(0), t.at(1) - c.at(1))
    }
    group(name: name, {
      set-origin(c)
      rotate(angle)
      // Facing left, mirror the icon so that its viewfinder stays on top.
      let a = calc.rem(angle / 1deg + 360, 360)
      scale(x: size, y: if a > 90 and a < 270 { -size } else { size })
      rect((-0.62, -0.2), (-0.2, 0.2), radius: 0.04, fill: p.body, stroke: 0.7pt + p.ink)
      rect((-0.52, 0.2), (-0.36, 0.28), fill: p.body, stroke: 0.6pt + p.ink)
      line((-0.2, -0.1), (0, -0.17), (0, 0.17), (-0.2, 0.1), close: true, fill: p.bg, stroke: 0.7pt + p.ink)
      anchor("lens", (0, 0))
      anchor("body", (-0.41, 0))
    })
    if label != none {
      let off = if label-side == "south" { (0, -0.45 * size) } else if label-side == "north" { (0, 0.5 * size) } else { (-0.95 * size, 0) }
      content((c.at(0) - 0.35 * size * calc.cos(angle) + off.at(0), c.at(1) - 0.35 * size * calc.sin(angle) + off.at(1)),
        text(size: 7.5pt, label))
    }
  })
}

// A path event. "emission": the small warm dot of an emission score;
// "scatter": an open blue circle; "null": an open blue circle with a centre
// dot; "absorb": a filled warm disc.
#let event(pos, kind: "scatter", size: 1) = {
  import cetz.draw: *
  let p = palette
  if kind == "emission" {
    circle(pos, radius: 0.06 * size, fill: p.warm, stroke: none)
  } else if kind == "scatter" {
    circle(pos, radius: 0.12 * size, fill: p.bg, stroke: 0.9pt + p.blue)
  } else if kind == "null" {
    circle(pos, radius: 0.13 * size, fill: p.bg, stroke: 0.9pt + p.blue)
    circle(pos, radius: 0.03 * size, fill: p.blue, stroke: none)
  } else if kind == "absorb" {
    circle(pos, radius: 0.13 * size, fill: p.warm, stroke: 0.9pt + p.warm)
  }
}

// A dotted surface normal from `pos` in direction `angle` (90deg is up),
// with an arrowhead (unless `arrow` is false) and a label beyond its tip.
#let normal-arrow(pos, angle: 90deg, length: 1.2, label: $bold(n)$, arrow: true) = {
  import cetz.draw: *
  let p = palette
  let tip = (pos.at(0) + length * calc.cos(angle), pos.at(1) + length * calc.sin(angle))
  line(pos, tip, stroke: (paint: p.ink2, thickness: 0.6pt, dash: "dotted"), mark: if arrow { (end: ">", fill: p.ink2) } else { none })
  if label != none {
    content((tip.at(0) + 0.25 * calc.cos(angle), tip.at(1) + 0.25 * calc.sin(angle)), text(size: 8pt, label))
  }
}

// An angle arc at `origin` from direction `from` to direction `to` (angles
// measured from +x), with its label at the middle of the arc.
#let angle-mark(origin, from, to, radius: 0.85, label: $theta$) = {
  import cetz.draw: *
  let p = palette
  let start = (origin.at(0) + radius * calc.cos(from), origin.at(1) + radius * calc.sin(from))
  arc(start, start: from, stop: to, radius: radius, stroke: 0.5pt + p.ink2)
  let mid = (from + to) / 2
  content((origin.at(0) + (radius + 0.25) * calc.cos(mid), origin.at(1) + (radius + 0.25) * calc.sin(mid)), text(size: 8pt, label))
}

// Where a label goes beside a point `m`, pushed `dist` along the unit vector
// `u` and then by `offset` (x, y): by default the anchor on the side facing
// `m`, so that the text grows away from it; `anchor` sets it instead.
#let _label-at(m, u, dist, body, offset: (0, 0), anchor: auto) = {
  import cetz.draw: content
  let anchor = if anchor != auto { anchor } else if u.at(0) > 0.4 { "west" } else if u.at(0) < -0.4 { "east" } else if u.at(1) > 0 { "south" } else { "north" }
  content((m.at(0) + dist * u.at(0) + offset.at(0), m.at(1) + dist * u.at(1) + offset.at(1)),
    anchor: anchor, body)
}

// A point, or an anchor name such as "light.front", as numbers (x, y) in the
// current coordinate system.
#let _xy(ctx, pos) = {
  let (_, v) = cetz.coordinate.resolve(ctx, pos)
  (v.at(0), v.at(1))
}

// A ray from `from` to `to`, each a point or an anchor. `kind` fixes its look,
// the same in every figure: "radiance" (solid blue: light towards the
// observer, or a path segment), "emission" (solid warm: radiance a surface or
// medium emits), "reflected" (dashed blue), "shadow" (dashed grey: a
// visibility query) and "missed" (dotted grey: a stretch that is never
// travelled). A `label` sits beside the point at `label-pos` of the way along,
// on the `label-side` ("left" or "right" of the direction of travel), clear of
// the line, moved by `label-offset` (x, y); `label-anchor` fixes which side
// of the text faces the line (by default the side towards it). `dash` and `thickness` override
// the kind's own. A named ray has the anchors "<name>.start", ".end", ".mid"
// and ".label" (where its label sits). `text-size` sets the label's size.
#let ray(from, to, kind: "radiance", thickness: auto, dash: auto, arrow: true, label: none,
         label-side: "left", label-pos: 0.5, label-dist: 0.22, label-offset: (0, 0), label-anchor: auto,
         text-size: 7.5pt, name: none) = {
  import cetz.draw: line, group, anchor, get-ctx
  let p = palette
  let styles = (
    radiance: (p.blue, none, 1.1pt),
    emission: (p.warm, none, 1.2pt),
    reflected: (p.blue, "dashed", 1.1pt),
    shadow: (p.neutral, "dashed", 0.8pt),
    missed: (p.ink2, "dotted", 0.6pt),
  )
  let (col, dash0, w) = styles.at(kind)
  let w = if thickness == auto { w } else { thickness }
  let dash = if dash == auto { dash0 } else { dash }
  get-ctx(ctx => {
    let a = _xy(ctx, from)
    let b = _xy(ctx, to)
    let d = (b.at(0) - a.at(0), b.at(1) - a.at(1))
    let n = calc.sqrt(d.at(0) * d.at(0) + d.at(1) * d.at(1))
    let sgn = if label-side == "left" { 1 } else { -1 }
    let u = (-sgn * d.at(1) / n, sgn * d.at(0) / n)
    let m = (a.at(0) + label-pos * d.at(0), a.at(1) + label-pos * d.at(1))
    group(name: name, {
      line(a, b, stroke: (paint: col, thickness: w, dash: dash),
        mark: if arrow { (end: ">", fill: col) } else { none })
      anchor("start", a)
      anchor("end", b)
      anchor("mid", (a.at(0) + d.at(0) / 2, a.at(1) + d.at(1) / 2))
      anchor("label", (m.at(0) + label-dist * u.at(0) + label-offset.at(0),
                       m.at(1) + label-dist * u.at(1) + label-offset.at(1)))
    })
    if label != none {
      _label-at(m, u, label-dist, text(size: text-size, fill: col, label), offset: label-offset, anchor: label-anchor)
    }
  })
}

// A surface seen edge-on: the boundary from `start` to `end`, with its
// material filled to `depth` on the `side` of that direction ("right" puts it
// below a boundary drawn left to right). `fill: none` leaves a bare boundary.
// A `label` is written inside the material, `label-pos` of the way along.
#let surface(start, end, depth: 0.35, side: "right", fill: palette.slab, stroke: 1pt + palette.ink2,
             label: none, label-pos: 0.5, name: none) = {
  import cetz.draw: line, content, group, anchor
  let d = (end.at(0) - start.at(0), end.at(1) - start.at(1))
  let n = calc.sqrt(d.at(0) * d.at(0) + d.at(1) * d.at(1))
  let s = if side == "right" { -1 } else { 1 }
  let u = (-s * d.at(1) / n, s * d.at(0) / n)
  let off(q, k) = (q.at(0) + k * u.at(0), q.at(1) + k * u.at(1))
  group(name: name, {
    if fill != none {
      line(start, end, off(end, depth), off(start, depth), close: true, fill: fill, stroke: none)
    }
    line(start, end, stroke: stroke)
    anchor("mid", (start.at(0) + d.at(0) / 2, start.at(1) + d.at(1) / 2))
  })
  if label != none {
    let m = (start.at(0) + label-pos * d.at(0), start.at(1) + label-pos * d.at(1))
    content(off(m, depth / 2), text(size: 7.5pt, fill: palette.ink2, label))
  }
}

// An emitting surface element: a warm bar of length `width` centred at `pos`
// (a point or an anchor), with `rays` short arrows of `ray-length` leaving its
// front face in the direction `angle` (90deg is up), or towards the point
// `aim` if one is given. Three texts follow the source when it moves or turns:
// `label` beyond the arrows, `header` above the source and `caption` below
// it, clear of the bar and the arrows at any angle, each moved by its own
// offset (x, y). Anchors: "<name>.center", ".front" (the tip
// of the middle arrow), ".back", ".left", ".right" (the ends of the bar, seen
// facing the emission) and ".ray-<i>", the tip of arrow i. `text-size` sets
// the size of the three texts.
#let light-source(pos, angle: 90deg, aim: none, width: 0.8, rays: 3, ray-length: 0.32, name: "light",
                  label: none, header: none, caption: none, text-size: 7.5pt,
                  label-offset: (0, 0), header-offset: (0, 0), caption-offset: (0, 0)) = {
  import cetz.draw: line, group, anchor, set-origin, rotate, get-ctx
  let p = palette
  get-ctx(ctx => {
    let c = _xy(ctx, pos)
    let angle = if aim == none { angle } else {
      let t = _xy(ctx, aim)
      calc.atan2(t.at(0) - c.at(0), t.at(1) - c.at(1))
    }
    let u = (calc.cos(angle), calc.sin(angle))
    group(name: name, {
      set-origin(c)
      rotate(angle - 90deg)
      line((-width / 2, 0), (width / 2, 0), stroke: 2pt + p.warm)
      for i in range(rays) {
        let x = -width / 2 + width * (i + 0.5) / rays
        line((x, 0.06), (x, 0.06 + ray-length), stroke: 0.7pt + p.warm, mark: (end: ">", fill: p.warm, scale: 0.5))
        anchor("ray-" + str(i), (x, 0.06 + ray-length))
      }
      anchor("center", (0, 0))
      anchor("front", (0, 0.06 + ray-length))
      anchor("back", (0, -0.06))
      anchor("left", (-width / 2, 0))
      anchor("right", (width / 2, 0))
    })
    if label != none {
      _label-at(c, u, ray-length + 0.28, text(size: text-size, fill: p.warm, label), offset: label-offset)
    }
    // vertical reach of the bar and of the arrows, above and below its centre
    let bar = calc.abs(calc.cos(angle)) * width / 2
    let reach = 0.06 + ray-length
    if header != none {
      _label-at(c, (0, 1), bar + calc.max(0, u.at(1)) * reach + 0.12,
        text(size: text-size, fill: p.warm, header), offset: header-offset)
    }
    if caption != none {
      _label-at(c, (0, -1), bar + calc.max(0, -u.at(1)) * reach + 0.12,
        text(size: text-size, fill: p.ink2, caption), offset: caption-offset)
    }
  })
}

// A participating medium filling the box from `from` to `to`. `fill` is the
// warm fill of the emitting media by default; `boundary` is none for an
// unbounded medium (air around a scene), "solid" or "dashed" for a bounded
// one. A `label` is written inside, at the `label-corner` ("north-west",
// "north-east", "south-west" or "south-east"). The box is named `name`.
#let medium(from, to, fill: palette.warm-fill, boundary: none, radius: 0, label: none,
            label-corner: "north-west", name: none) = {
  import cetz.draw: rect, content
  let p = palette
  let stroke = if boundary == none { none } else { (paint: p.ink2, thickness: 0.6pt, dash: if boundary == "dashed" { "dashed" } else { none }) }
  rect(from, to, fill: fill, stroke: stroke, radius: radius, name: name)
  if label != none {
    let x0 = calc.min(from.at(0), to.at(0))
    let x1 = calc.max(from.at(0), to.at(0))
    let y0 = calc.min(from.at(1), to.at(1))
    let y1 = calc.max(from.at(1), to.at(1))
    let i = 0.12
    let pos = (
      "north-west": (x0 + i, y1 - i), "north-east": (x1 - i, y1 - i),
      "south-west": (x0 + i, y0 + i), "south-east": (x1 - i, y0 + i),
    ).at(label-corner)
    content(pos, anchor: label-corner, text(size: 7.5pt, fill: p.ink2, label))
  }
}

// The point at `angle` on a circle of `radius` around `pos`, pushed `out`
// beyond it: where a ray meets an emitter object, or where its label goes.
#let on-boundary(pos, radius, angle, out: 0) = (
  pos.at(0) + (radius + out) * calc.cos(angle),
  pos.at(1) + (radius + out) * calc.sin(angle),
)

// An emitting object at temperature T, seen in cross-section as a disc of
// `radius` around `pos` (a point or an anchor). kind "surface" is an opaque
// body, which emits from its boundary (solid outline); kind "volume" is a
// bounded emitting medium (a warm fill darker than the air of `medium`,
// dashed outline). `fill` overrides the kind's fill, for a particular
// material. `rays` is either a number of emission arrows spread evenly around
// the boundary, the first at `ray-start`, or a list of their directions.
// `label` is written inside the disc, `caption` below it, each moved by its
// offset (x, y), in `text-size`. Anchors: "<name>.center", ".ray-<i>" (the tip of arrow i)
// and the disc's own "north", "south", "east" and "west".
#let emitter-object(pos, radius: 1, kind: "surface", fill: auto, rays: (), ray-start: 90deg,
                    ray-length: 0.35, label: none, label-fill: palette.ink, caption: none,
                    label-offset: (0, 0), caption-offset: (0, 0), text-size: 7.5pt, name: none) = {
  import cetz.draw: circle, line, content, group, anchor, get-ctx
  let p = palette
  let (fill0, stroke) = if kind == "volume" {
    (p.warm-fill, (paint: p.ink2, thickness: 0.6pt, dash: "dashed"))
  } else {
    (p.slab, 1pt + p.ink2)
  }
  let angles = if type(rays) == int {
    range(rays).map(i => ray-start + i * 360deg / rays)
  } else { rays }
  get-ctx(ctx => {
    let c = _xy(ctx, pos)
    group(name: name, {
      circle(c, radius: radius, fill: if fill == auto { fill0 } else { fill }, stroke: stroke)
      for (i, a) in angles.enumerate() {
        let tip = on-boundary(c, radius, a, out: 0.06 + ray-length)
        line(on-boundary(c, radius, a, out: 0.06), tip,
          stroke: 0.7pt + p.warm, mark: (end: ">", fill: p.warm, scale: 0.5))
        anchor("ray-" + str(i), tip)
      }
      anchor("center", c)
      anchor("north", (c.at(0), c.at(1) + radius))
      anchor("south", (c.at(0), c.at(1) - radius))
      anchor("east", (c.at(0) + radius, c.at(1)))
      anchor("west", (c.at(0) - radius, c.at(1)))
    })
    if label != none {
      content((c.at(0) + label-offset.at(0), c.at(1) + label-offset.at(1)), text(size: text-size, fill: label-fill, label))
    }
    if caption != none {
      content((c.at(0) + caption-offset.at(0), c.at(1) - radius - 0.12 + caption-offset.at(1)),
        anchor: "north", text(size: text-size, fill: p.ink2, caption))
    }
  })
}

// The image plane of a camera seen edge-on: a vertical column of `pixels`
// cells of total `height`, centred at `center` (a point or an anchor). The
// cells whose index is in `highlight` are filled in `hl-fill` (index 0 is the
// top cell). Anchors: "<name>.px-<i>" (the centre of cell i), "<name>.top",
// "<name>.bottom" and "<name>.x" (any point on the plane shares its x).
#let image-plane(center, height: 2.4, pixels: 8, width: 0.16, highlight: (), hl-fill: palette.blue-fill,
                 hl-stroke: palette.engines, name: "plane") = {
  import cetz.draw: rect, group, anchor, get-ctx
  let p = palette
  get-ctx(ctx => {
    let c = _xy(ctx, center)
    let h = height / pixels
    let top = c.at(1) + height / 2
    group(name: name, {
      for i in range(pixels) {
        let y0 = top - (i + 1) * h
        let lit = i in highlight
        rect((c.at(0) - width / 2, y0), (c.at(0) + width / 2, y0 + h),
          fill: if lit { hl-fill } else { p.slab },
          stroke: if lit { 0.7pt + hl-stroke } else { 0.5pt + p.ink2 })
        anchor("px-" + str(i), (c.at(0), y0 + h / 2))
      }
      anchor("top", (c.at(0), top))
      anchor("bottom", (c.at(0), top - height))
      anchor("x", c)
    })
  })
}

// Text at a point or an anchor, moved by `offset` (x, y), with the given
// `anchor` of the text on that point.
#let note(pos, body, offset: (0, 0), anchor: "center", size: 7.5pt, fill: palette.ink2) = {
  import cetz.draw: content, get-ctx
  get-ctx(ctx => {
    let c = _xy(ctx, pos)
    content((c.at(0) + offset.at(0), c.at(1) + offset.at(1)), anchor: anchor, text(size: size, fill: fill, body))
  })
}
