"""WCAG 2.2 SC 1.4.3 calculations and explicit high-contrast Word remediation."""
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


def luminance(rgb):
    channels = [int(rgb[i:i+2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return sum(c * weight for c, weight in zip(linear, (0.2126, 0.7152, 0.0722)))


def contrast_ratio(foreground, background):
    a, b = sorted((luminance(foreground), luminance(background)))
    return (b + 0.05) / (a + 0.05)


def minimum_ratio(points=None, bold=False):
    return 3.0 if points is not None and (points >= 18 or bold and points >= 14) else 4.5


def set_property(parent, name, attributes):
    for child in list(parent.findall(qn('w:' + name))):
        parent.remove(child)
    child = OxmlElement('w:' + name)
    for key, value in attributes.items():
        child.set(qn('w:' + key), value)
    parent.append(child)


def normalize_contrast(doc):
    """Guarantee explicit black/white for editable w:r text, not rendered images.

    Original color meaning must be reviewed. Source diagnostics deliberately do
    not pretend to resolve Word theme/style/table-style/background inheritance.
    """
    roots = [doc.element]
    for section in doc.sections:
        roots.extend([section.header._element, section.footer._element])
    # Linked headers share a root; count and change each once.
    roots = list({id(root): root for root in roots}.values())
    count = failures = 0
    examples = []
    for root in roots:
        for run in root.xpath('.//w:r'):
            texts = run.xpath('./w:t | ./w:instrText')
            if not texts or not ''.join(t.text or '' for t in texts).strip():
                continue
            count += 1
            rpr = run.find(qn('w:rPr'))
            if rpr is None:
                rpr = OxmlElement('w:rPr'); run.insert(0, rpr)
            color = rpr.find(qn('w:color'))
            foreground = color.get(qn('w:val')) if color is not None else None
            # Report an explicit source color against white only as a diagnostic,
            # rather than claiming the source's rendered background is known.
            if foreground and len(foreground) == 6 and not color.get(qn('w:themeColor')):
                try:
                    ratio = contrast_ratio(foreground, 'FFFFFF')
                    if ratio < 4.5:
                        failures += 1
                        if len(examples) < 5:
                            label = ''.join(t.text or '' for t in texts)[:100]
                            examples.append(f'"{label}" (#{foreground} against white: {ratio:.2f}:1)')
                except ValueError:
                    pass
            set_property(rpr, 'color', {'val': '000000'})
            set_property(rpr, 'shd', {'val': 'clear', 'color': 'auto', 'fill': 'FFFFFF'})
            for highlight in list(rpr.findall(qn('w:highlight'))):
                rpr.remove(highlight)
            if run.getparent().tag == qn('w:hyperlink'):
                set_property(rpr, 'u', {'val': 'single'})
        for paragraph in root.xpath('.//w:p'):
            ppr = paragraph.find(qn('w:pPr'))
            if ppr is None:
                ppr = OxmlElement('w:pPr'); paragraph.insert(0, ppr)
            set_property(ppr, 'shd', {'val': 'clear', 'color': 'auto', 'fill': 'FFFFFF'})
        for cell in root.xpath('.//w:tc'):
            tcpr = cell.find(qn('w:tcPr'))
            if tcpr is None:
                tcpr = OxmlElement('w:tcPr'); cell.insert(0, tcpr)
            set_property(tcpr, 'shd', {'val': 'clear', 'color': 'auto', 'fill': 'FFFFFF'})
    set_property(doc.element, 'background', {'color': 'FFFFFF'})
    # w:background precedes body in the document schema.
    background = doc.element.find(qn('w:background'))
    doc.element.remove(background); doc.element.insert(0, background)
    changes = [f'WCAG 2.2 SC 1.4.3: applied explicit black text on white backgrounds to {count} editable text runs (21:1). Removed highlights, replaced paragraph/cell shading, and underlined hyperlinks.']
    if failures:
        changes.append(f'Found {failures} explicit source text colors below 4.5:1 when compared against white; this diagnostic does not resolve original inherited backgrounds. Examples: ' + '; '.join(examples))
    review = ['High-contrast mode changes color formatting. Check any meaning originally communicated by color (WCAG 1.4.1).',
              'Contrast verification covers editable Word text formatting only. Images of text, charts, drawing backgrounds, WordArt, annotations, footnotes/endnotes, and other unsupported parts require rendered review. Full WCAG conformance is not established.']
    return changes, review
