// Components adapted from stuxf/basic-typst-resume-template v0.2.9 (Unlicense,
// https://github.com/stuxf/basic-typst-resume-template).
// Changes: no Typst Universe import (the build is offline), no small caps, no
// justification, no hyphenation, no ligatures, and every visible word comes from
// the render model built by scripts/cvlib.py. The only literals here are
// separators, which scripts/check_pdf.py relies on to detect hidden text.

#let opt(d, key) = d.at(key, default: none)

#let setup(meta, basics, body) = {
  set document(title: meta.title, author: basics.name, date: none)
  set text(
    font: "New Computer Modern",
    size: 10pt,
    lang: "en",
    region: "us",
    hyphenate: false,
    ligatures: false,
  )
  set page(
    paper: "us-letter",
    margin: (x: 0.6in, y: 0.5in),
    footer: align(center, text(size: 8pt, fill: luma(90))[#basics.name · #meta.version]),
  )
  set par(justify: false, leading: 0.6em, spacing: 0.7em)
  set list(indent: 0.4em, body-indent: 0.5em, spacing: 0.55em)

  show heading.where(level: 1): it => {
    set align(center)
    set text(size: 20pt, weight: 700)
    block(below: 0.6em, it.body)
  }
  show heading.where(level: 2): it => {
    set text(size: 11pt, weight: 700)
    block(above: 1.1em, below: 0.6em, width: 100%)[
      #it.body
      #v(-0.7em)
      #line(length: 100%, stroke: 0.6pt)
    ]
  }
  body
}

#let header(b) = {
  heading(level: 1, b.name)
  align(center)[
    #text(size: 11pt, b.label)
    #v(0.1em)
    #{
      let items = (b.location_line,)
      if opt(b, "phone") != none { items.push(b.phone) }
      items.push(link("mailto:" + b.email, b.email))
      if opt(b, "url") != none { items.push(link(b.url, b.url_display)) }
      for p in b.profiles { items.push(link(p.url, p.display)) }
      items.join("  |  ")
    }
  ]
}

// Two rows, each with a left and a right part (title/dates, place/location).
#let entry-head(left-top, right-top, left-bottom: none, right-bottom: none) = {
  block(below: 0.45em, breakable: false)[
    #left-top #h(1fr) #right-top
    #if left-bottom != none or right-bottom != none [
      \ #left-bottom #h(1fr) #right-bottom
    ]
  ]
}

#let bullets(items) = {
  if items.len() > 0 { list(..items.map(h => h.text)) }
}

#let summary-section(b) = block(b.summary)

#let skills-section(skills) = {
  for g in skills {
    block(below: 0.45em)[#strong(g.name + ":") #g.keywords.join(", ")]
  }
}

#let work-section(work) = {
  for w in work {
    if w.compact {
      block(below: 0.55em)[#strong(w.position), #w.name #h(1fr) #w.dates]
    } else {
      entry-head(
        strong(w.position),
        w.dates,
        left-bottom: w.name,
        right-bottom: if opt(w, "location") != none { emph(w.location) },
      )
      if opt(w, "summary") != none { block(below: 0.5em, emph(w.summary)) }
      bullets(w.highlights)
      v(0.4em)
    }
  }
}

#let projects-section(projects) = {
  for p in projects {
    let right = ()
    if opt(p, "url") != none { right.push(link(p.url, p.url_display)) }
    if opt(p, "dates") != none { right.push(p.dates) }
    entry-head(strong(p.name), right.join("  |  "))
    if opt(p, "description") != none { block(below: 0.5em, p.description) }
    bullets(p.highlights)
    if p.keywords.len() > 0 { block(below: 0.6em, emph(p.keywords.join(", "))) }
  }
}

#let education-section(education) = {
  for e in education {
    let degree = (opt(e, "studyType"), opt(e, "area")).filter(x => x != none).join(", ")
    entry-head(strong(e.institution), opt(e, "dates"), left-bottom: degree)
  }
}

#let certificates-section(certificates) = {
  for c in certificates {
    block(below: 0.45em)[
      #strong(c.name)#if opt(c, "issuer") != none [, #c.issuer] #h(1fr) #opt(c, "date_display")
    ]
  }
}

#let languages-section(languages) = {
  block(languages.map(l => l.language + " (" + l.fluency + ")").join("  ·  "))
}

#let render-section(s, data) = {
  heading(level: 2, s.title)
  if s.key == "summary" { summary-section(data.basics) }
  else if s.key == "skills" { skills-section(data.skills) }
  else if s.key == "work" { work-section(data.work) }
  else if s.key == "projects" { projects-section(data.projects) }
  else if s.key == "education" { education-section(data.education) }
  else if s.key == "certificates" { certificates-section(data.certificates) }
  else if s.key == "languages" { languages-section(data.languages) }
  else { panic("unknown section: " + s.key) }
}
