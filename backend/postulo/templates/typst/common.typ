// Shared settings of the Postulo documents (docs/SPEC.md sections 7.2 and 7.5).
// Every text comes from data.json, inserted as plain strings: nothing is
// interpreted as markup, so no escaping is ever needed.

#let setup(d, body) = {
  let L = d.layout
  set document(title: d.meta_title, author: d.name)
  set page(paper: "a4", margin: (x: L.margin_x * 1mm, y: L.margin_y * 1mm))
  // ATS rules: no ligatures, no hyphenation, left aligned.
  set text(
    font: L.font,
    lang: d.lang,
    size: L.size * 1pt,
    fill: rgb(L.ink),
    ligatures: false,
    discretionary-ligatures: false,
    historical-ligatures: false,
    hyphenate: false,
  )
  set par(justify: false, leading: L.leading * 1em, spacing: L.leading * 1.6em)
  set list(marker: [•], indent: 0.2em, body-indent: 0.5em, spacing: L.leading * 1em)
  // Links stay visible: accent color (modern) or underlined (classic, all black).
  show link: it => if L.template == "classic" { underline(offset: 1.5pt, it) } else {
    text(fill: rgb(L.accent), it)
  }
  body
}

// Name on the first line, then contact details in the body (not in a header).
#let identity(d, subtitle: none) = {
  let L = d.layout
  text(size: L.size * 2.0pt, weight: "bold", fill: rgb(L.accent), d.name)
  if subtitle != none and subtitle != "" {
    linebreak()
    text(size: L.size * 1.15pt, weight: "semibold", subtitle)
  }
  linebreak()
  let parts = ()
  if d.contact.city != "" { parts.push(d.contact.city) }
  // box: a link is never split across two lines (it would break the URL text).
  for l in d.contact.links { parts.push(box(link(l.url, l.label))) }
  text(size: L.size * 0.95pt, parts.join(" | "))
}
