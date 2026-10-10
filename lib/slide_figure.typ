// Page setup for a diagram compiled on its own to assets/diagrams/<stem>.svg
// and placed on a slide: the page hugs the drawing, the background stays
// transparent so the slide shows through, and text uses the deck's fonts
// (compile with --font-path assets/fonts).
//
//   #import "/lib/slide_figure.typ": slide-figure, cetz
//   #show: slide-figure
//   #cetz.canvas({ ... })
#import "@preview/cetz:0.5.2"
#import "/lib/diagram_parts.typ": palette

#let slide-figure(body) = {
  set page(width: auto, height: auto, margin: 4pt, fill: none)
  set text(font: "Inter", size: 11pt, fill: palette.ink, lang: "es")
  show raw: set text(font: "Fira Code")
  body
}
