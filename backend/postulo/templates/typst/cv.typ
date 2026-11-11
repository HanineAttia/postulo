// Postulo CV, one column (docs/SPEC.md sections 7.1, 7.2, 7.5 and 16.1).
// The "modern" and "classic" models differ only by data.layout (font, colors).
#import "common.typ": setup, contact-line

#let d = json("data.json")
#let L = d.layout
#let accent = rgb(L.accent)
#let small = L.size * 0.95pt

#show: body => setup(d, body)

// Header: name (large, bold), position on the next line, contact details.
#block(below: 7pt, text(size: L.size * 2.1pt, weight: "bold", fill: accent, d.name))
#if d.title != "" {
  block(below: 5pt, text(size: L.size * 1.15pt, weight: "semibold", d.title))
}
#block(above: 0pt, text(size: small, contact-line(d)))

#if d.summary != "" {
  v(8pt, weak: true)
  block(par(d.summary))
}

#let section-title(title) = {
  v(L.leading * 1em + L.section_gap * 1pt, weak: true)
  block(
    width: 100%,
    below: 4pt,
    stroke: (bottom: 0.6pt + accent),
    inset: (bottom: 2.5pt),
    text(size: L.size * 1.12pt, weight: "bold", fill: accent, title),
  )
}

// Two lines in a two-column grid: title | dates, then organization | city.
// Only the left column wraps; the dates always stay on the first line, right-aligned.
#let entry(e) = {
  // 5 pt on top of the normal line spacing, so entries stand apart from their bullets.
  block(above: L.leading * 1em + L.entry_gap * 1pt, below: 0pt, breakable: true, {
    let head = if e.url != none { link(e.url, e.title) } else { e.title }
    let cells = (text(weight: "bold", head), align(right, text(size: small, e.dates)))
    if e.subtitle != "" or e.location != "" {
      cells.push(text(style: "italic", e.subtitle))
      cells.push(align(right, text(size: small, style: "italic", e.location)))
    }
    grid(columns: (1fr, auto), column-gutter: 12pt, row-gutter: L.leading * 1em, ..cells)
    if e.details != "" {
      block(above: L.leading * 1em + L.bullet_gap * 1pt, below: 0pt, text(size: small, e.details))
    }
    if e.bullets.len() > 0 {
      block(above: L.leading * 1em + L.bullet_gap * 1pt, below: 0pt, list(
        marker: [•],
        indent: 0.25em,
        body-indent: 0.55em,
        spacing: L.bullet_gap * 1pt + L.leading * 1em,
        ..e.bullets.map(b => [#b]),
      ))
    }
  })
}

#for s in d.sections {
  section-title(s.title)
  for e in s.entries { entry(e) }
  for line in s.lines {
    block(above: L.bullet_gap * 1pt + L.leading * 1em, below: 0pt, {
      if line.label != "" {
        // French typography: no-break space before the colon.
        let sep = if d.lang == "fr" { "\u{00a0}: " } else { ": " }
        text(weight: "bold", line.label + sep)
      }
      line.text
    })
  }
}
