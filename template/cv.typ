// Entry point. Renders one variant from its render model:
//   typst compile --root . --input data=/build/<variant>/resolved.json template/cv.typ out.pdf
// The model is produced by scripts/resolve.py; this file never reads cv.yaml.

#import "components.typ": setup, header, render-section

#let data = json(sys.inputs.at("data"))

#show: body => setup(data.meta, data.basics, body)

#header(data.basics)

#for s in data.sections {
  render-section(s, data)
}
