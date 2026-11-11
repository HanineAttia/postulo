// Shared settings of the Postulo documents (docs/SPEC.md sections 7.2, 7.5 and 16.1).
// Every text comes from data.json, inserted as plain strings: nothing is
// interpreted as markup, so no escaping is ever needed.

#let setup(d, body, margin-x: none, margin-y: none) = {
  let L = d.layout
  set document(title: d.meta_title, author: d.name)
  set page(
    paper: L.paper,
    margin: (
      x: if margin-x == none { L.margin_x * 1mm } else { margin-x },
      y: if margin-y == none { L.margin_y * 1mm } else { margin-y },
    ),
  )
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
  set par(justify: false, leading: L.leading * 1em, spacing: L.leading * 1em)
  // Links stay visible: accent color (modern) or underlined (classic, all black).
  show link: it => if L.template == "classic" { underline(offset: 1.5pt, it) } else {
    text(fill: rgb(L.accent), it)
  }
  body
}

// Contact details in the body (never in a page header), spaced separators (SPEC 16.1).
#let contact-line(d) = {
  let parts = ()
  if d.contact.city != "" { parts.push(d.contact.city) }
  // box: a link is never split across two lines (it would break the URL text).
  for l in d.contact.links { parts.push(box(link(l.url, l.label))) }
  parts.join([#h(0.45em)·#h(0.45em)])
}
