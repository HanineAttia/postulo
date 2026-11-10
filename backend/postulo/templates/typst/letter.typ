// Postulo cover letter, same visual model as the CV (docs/SPEC.md sections 7.3, 7.5).
#import "common.typ": setup, identity

#let d = json("data.json")
#let L = d.layout

#show: body => setup(d, body)
#set par(spacing: 1.0em, leading: L.leading * 1.15em)

#identity(d)

#v(1.6em)
#for line in d.recipient { [#line #linebreak()] }
#if d.place_date != "" { align(left, d.place_date) }

#if d.subject != "" {
  v(0.8em)
  text(weight: "bold", d.subject)
}

#v(0.8em)
#par(d.salutation)
#for p in d.paragraphs { par(p) }
#par(d.closing)
#v(0.8em)
#par(d.name)
