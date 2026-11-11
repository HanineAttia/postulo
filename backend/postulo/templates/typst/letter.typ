// Postulo cover letter, same font and colors as the CV (docs/SPEC.md sections 7.3 and 16.1).
#import "common.typ": setup

#let d = json("data.json")
#let L = d.layout

// Letter margins of 22 to 25 mm, whatever the CV compaction (SPEC 16.1).
#show: body => setup(d, body, margin-x: 24mm, margin-y: 22mm)
#set par(leading: 0.62em, spacing: 10pt)

// Sender (top left): name in bold, then contact details, one per line.
#block({
  text(weight: "bold", size: L.size * 1.25pt, fill: rgb(L.accent), d.name)
  set text(size: L.size * 0.95pt)
  if d.contact.city != "" { linebreak(); d.contact.city }
  for l in d.contact.links { linebreak(); link(l.url, l.label) }
})

// Recipient: organization, recruitment team, city (French layout: right half of the page).
#if d.recipient.len() > 0 {
  v(14pt)
  align(right, block(width: 46%, align(left, d.recipient.map(r => [#r]).join(linebreak()))))
}

// Place and date on one line, right-aligned.
#v(14pt)
#align(right, d.place_date)

// Balanced page: the free space is shared above and below the body.
#v(1fr)
#if d.subject != "" {
  block(below: 14pt, text(weight: "bold", d.subject))
}
#par(d.salutation)
#for p in d.paragraphs { par(p) }
#par(d.closing)
#v(16pt)
#par(d.name)
#v(1.6fr)
