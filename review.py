"""Employee-confirmed edits on a Word copy. Never infer image meaning."""
from io import BytesIO
from base64 import b64encode
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph


def roots(doc):
    result=[doc.element]; seen={id(doc.element)}
    for section in doc.sections:
        for part in [section.header,section.footer]:
            if id(part._element) not in seen:
                result.append(part._element); seen.add(id(part._element))
    return result


def elements(doc, query):
    return [e for root in roots(doc) for e in root.xpath(query)]


def minimum_text(doc):
    count=0
    for r in elements(doc,'.//w:r[w:t]'):
        pr=r.find(qn('w:rPr'))
        size=pr.find(qn('w:sz')) if pr is not None else None
        effective = int(size.get(qn('w:val'),'24')) if size is not None else None
        if effective is None:
            style_ids = r.xpath('./w:rPr/w:rStyle/@w:val')
            parents=r.xpath('ancestor::w:p[1]')
            if parents:style_ids += parents[0].xpath('./w:pPr/w:pStyle/@w:val')
            for style_id in style_ids:
                style=next((s for s in doc.styles if s.style_id==style_id),None)
                seen=set()
                while style is not None and style.style_id not in seen:
                    seen.add(style.style_id)
                    if style.font.size is not None:
                        effective=int(style.font.size.pt*2);break
                    style=style.base_style
                if effective is not None:break
        if effective is not None and effective<24:
            if pr is None:pr=OxmlElement('w:rPr');r.insert(0,pr)
            if size is None:size=OxmlElement('w:sz');pr.append(size)
            size.set(qn('w:val'),'24');count+=1
            cs=pr.find(qn('w:szCs'))
            if cs is not None:cs.set(qn('w:val'),'24')
    return count


def manifest(data):
    doc=Document(BytesIO(data)); result={'headings':[],'images':[],'tables':[],'links':[]}
    previous=0
    for i,p in enumerate(elements(doc,'.//w:p')):
        para=Paragraph(p,doc);style=para.style.name
        if style.startswith('Heading ') and style.split()[-1].isdigit():
            level=int(style.split()[-1]); suggested=min(level,previous+1)
            result['headings'].append({'id':i,'text':para.text,'level':level,'suggested':suggested})
            previous=suggested
    for i,image in enumerate(elements(doc,'.//*[local-name()="docPr"]')):
        item={'id':i,'name':image.get('name','Image'),'alt':image.get('descr',''),'preview':None}
        # Show embedded raster content only, never execute SVG/HTML from uploads.
        ancestor=image.getparent()
        if ancestor is not None:
            blips=ancestor.xpath('.//*[local-name()="blip"]')
            if blips:
                rid=blips[0].get(qn('r:embed'))
                for part in [doc.part]+[s.header.part for s in doc.sections]+[s.footer.part for s in doc.sections]:
                    if image.getroottree().getroot() is part.element and rid in part.rels:
                        target=part.rels[rid].target_part
                        if target.content_type in ('image/png','image/jpeg','image/gif') and len(target.blob)<3_000_000:
                            item['preview']='data:'+target.content_type+';base64,'+b64encode(target.blob).decode()
                        break
        result['images'].append(item)
    for i,table in enumerate(elements(doc,'.//w:tbl')):
        rows=table.findall(qn('w:tr'))
        preview=[]
        for row in rows:
            preview.append([' '.join(c.xpath('.//w:t/text()')) for c in row.findall(qn('w:tc'))])
        result['tables'].append({'id':i,'rows':preview[:20],'truncated':len(rows)>20,
            'header':bool(rows and rows[0].xpath('./w:trPr/w:tblHeader[not(@w:val="0") and not(@w:val="false")]')),
            'complex':bool(table.xpath('.//w:gridSpan | .//w:vMerge | .//w:tc/w:tbl'))})
    for i,link in enumerate(elements(doc,'.//w:hyperlink')):
        rid=link.get(qn('r:id'));target=''
        for part in [doc.part]+[s.header.part for s in doc.sections]+[s.footer.part for s in doc.sections]:
            if link.getroottree().getroot() is part.element and rid in part.rels:
                target=part.rels[rid].target_ref;break
        result['links'].append({'id':i,'label':''.join(link.xpath('.//w:t/text()')),'target':target})
    return result


def apply_review(data, edits):
    if not isinstance(edits,dict):raise ValueError('Review edits must be an object.')
    doc=Document(BytesIO(data));changes=[]
    queries={'headings':'.//w:p','images':'.//*[local-name()="docPr"]','tables':'.//w:tbl','links':'.//w:hyperlink'}
    nodes={k:elements(doc,q) for k,q in queries.items()}
    for group in queries:
        items=edits.get(group,[])
        if not isinstance(items,list) or len(items)>2000:raise ValueError('Invalid review entries.')
        seen=set()
        for item in sorted(items,key=lambda x:x.get('id',-1),reverse=group=='tables'):
            i=item.get('id')
            if type(i) is not int or i<0 or i>=len(nodes[group]) or i in seen:raise ValueError('Invalid or repeated review item. Reload the review.')
            seen.add(i);node=nodes[group][i]
            if group=='headings':
                level=item.get('level')
                if type(level) is not int or not 1<=level<=6:raise ValueError('Heading levels must be from 1 to 6.')
                Paragraph(node,doc).style='Heading '+str(level)
                changes.append(f'Heading set to level {level}: '+Paragraph(node,doc).text)
            elif group=='images':
                alt=item.get('alt','')
                if not isinstance(alt,str) or len(alt)>2000:raise ValueError('Image descriptions must be under 2,000 characters.')
                if alt.strip():
                    node.set('descr',alt.strip());changes.append(f'Employee supplied alt text for image {i+1}.')
            elif group=='links':
                label=item.get('label','')
                if not isinstance(label,str) or not label.strip() or len(label)>1000:raise ValueError('Provide a nonempty link label under 1,000 characters.')
                texts=node.xpath('.//w:t')
                if not texts:raise ValueError('This link has no editable text; edit it in Word.')
                texts[0].text=label.strip()
                for t in texts[1:]:t.text=''
                changes.append('Employee updated link label: '+label.strip())
            elif group=='tables':
                action=item.get('action','keep')
                if action not in ('keep','header','no-header','simplify'):raise ValueError('Unknown table action.')
                if action=='simplify':
                    if item.get('confirmed') is not True:raise ValueError('Confirm the table preview before simplifying.')
                    # Move actual cell content, retaining images/links/paragraphs,
                    # rather than duplicating merged-cell text or dropping objects.
                    for row in node.findall(qn('w:tr')):
                        for cell in row.findall(qn('w:tc')):
                            for child in list(cell):
                                if child.tag in (qn('w:p'),qn('w:tbl')):node.addprevious(child)
                    node.getparent().remove(node)
                    changes.append(f'Table {i+1} converted to sequential cell content after employee confirmation; review order and relationships.')
                elif action in ('header','no-header'):
                    rows=node.findall(qn('w:tr'))
                    if rows:
                        pr=rows[0].find(qn('w:trPr'))
                        if pr is None:pr=OxmlElement('w:trPr');rows[0].insert(0,pr)
                        for header in list(pr.findall(qn('w:tblHeader'))):pr.remove(header)
                        if action=='header':pr.append(OxmlElement('w:tblHeader'))
                        changes.append(f'Table {i+1}: employee '+('designated' if action=='header' else 'removed')+' the first-row header setting.')
    output=BytesIO();doc.save(output)
    return output.getvalue(),changes
