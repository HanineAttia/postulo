// Postulo CV, one column (docs/SPEC.md sections 7.1, 7.2, 7.5).
// The "modern" and "classic" models differ only by data.layout (font, colors).
#import "common.typ": setup, identity

#let d = json("data.json")
#let L = d.layout
#let accent = rgb(L.accent)

#show: body => setup(d, body)

#let section-title(title) = {
  v(L.gap * 1mm, weak: true)
  block(
    width: 100%,
    below: 0.45em,
    stroke: (bottom: 0.6pt + accent),
    inset: (bottom: 0.18em),
    text(size: L.size * 1.12pt, weight: "bold", fill: accent, title),
  )
}

#let entry(e) = {
  block(above: L.item_gap * 1mm, below: 0pt, breakable: true, {
    let head = if e.url != none { link(e.url, e.title) } else { e.title }
    text(weight: "bold", head)
    if e.subtitle != "" { [, ] + e.subtitle }
    if e.location != "" { [, ] + e.location }
    if e.dates != "" { h(1fr) + box(text(size: L.size * 0.95pt, e.dates)) }
    if e.details != "" {
      linebreak()
      text(size: L.size * 0.95pt, e.details)
    }
    if e.bullets.len() > 0 {
      v(0.3em, weak: true)
      list(..e.bullets.map(b => [#b]))
    }
  })
}

#identity(d, subtitle: d.title)

#if d.summary != "" {
  v(0.75em, weak: true)
  par(d.summary)
}

#for s in d.sections {
  section-title(s.title)
  for e in s.entries { entry(e) }
  for line in s.lines {
    block(above: L.item_gap * 0.8mm, below: 0pt, {
      if line.label != "" {
        // French typography: no-break space before the colon.
        let sep = if d.lang == "fr" { "\u{00a0}: " } else { ": " }
        text(weight: "semibold", line.label + sep)
      }
      line.text
    })
  }
}
