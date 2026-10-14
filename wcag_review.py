"""Full WCAG 2.2 criterion inventory; review framework, not certification.

WCAG is a web standard. Apply WCAG2ICT guidance when interpreting it for
non-web Word/PDF files. Human applicability decisions are required.
"""
SOURCE = 'https://www.w3.org/TR/WCAG22/'
ICT_SOURCE = 'https://www.w3.org/TR/wcag2ict/'
# WCAG 2.2 removes the obsolete 4.1.1 Parsing criterion.
INVENTORY = '''
1.1.1|A|Non-text Content
1.2.1|A|Audio-only and Video-only (Prerecorded)
1.2.2|A|Captions (Prerecorded)
1.2.3|A|Audio Description or Media Alternative (Prerecorded)
1.2.4|AA|Captions (Live)
1.2.5|AA|Audio Description (Prerecorded)
1.2.6|AAA|Sign Language (Prerecorded)
1.2.7|AAA|Extended Audio Description (Prerecorded)
1.2.8|AAA|Media Alternative (Prerecorded)
1.2.9|AAA|Audio-only (Live)
1.3.1|A|Info and Relationships
1.3.2|A|Meaningful Sequence
1.3.3|A|Sensory Characteristics
1.3.4|AA|Orientation
1.3.5|AA|Identify Input Purpose
1.3.6|AAA|Identify Purpose
1.4.1|A|Use of Color
1.4.2|A|Audio Control
1.4.3|AA|Contrast (Minimum)
1.4.4|AA|Resize Text
1.4.5|AA|Images of Text
1.4.6|AAA|Contrast (Enhanced)
1.4.7|AAA|Low or No Background Audio
1.4.8|AAA|Visual Presentation
1.4.9|AAA|Images of Text (No Exception)
1.4.10|AA|Reflow
1.4.11|AA|Non-text Contrast
1.4.12|AA|Text Spacing
1.4.13|AA|Content on Hover or Focus
2.1.1|A|Keyboard
2.1.2|A|No Keyboard Trap
2.1.3|AAA|Keyboard (No Exception)
2.1.4|A|Character Key Shortcuts
2.2.1|A|Timing Adjustable
2.2.2|A|Pause, Stop, Hide
2.2.3|AAA|No Timing
2.2.4|AAA|Interruptions
2.2.5|AAA|Re-authenticating
2.2.6|AAA|Timeouts
2.3.1|A|Three Flashes or Below Threshold
2.3.2|AAA|Three Flashes
2.3.3|AAA|Animation from Interactions
2.4.1|A|Bypass Blocks
2.4.2|A|Page Titled
2.4.3|A|Focus Order
2.4.4|A|Link Purpose (In Context)
2.4.5|AA|Multiple Ways
2.4.6|AA|Headings and Labels
2.4.7|AA|Focus Visible
2.4.8|AAA|Location
2.4.9|AAA|Link Purpose (Link Only)
2.4.10|AAA|Section Headings
2.4.11|AA|Focus Not Obscured (Minimum)
2.4.12|AAA|Focus Not Obscured (Enhanced)
2.4.13|AAA|Focus Appearance
2.5.1|A|Pointer Gestures
2.5.2|A|Pointer Cancellation
2.5.3|A|Label in Name
2.5.4|A|Motion Actuation
2.5.5|AAA|Target Size (Enhanced)
2.5.6|AAA|Concurrent Input Mechanisms
2.5.7|AA|Dragging Movements
2.5.8|AA|Target Size (Minimum)
3.1.1|A|Language of Page
3.1.2|AA|Language of Parts
3.1.3|AAA|Unusual Words
3.1.4|AAA|Abbreviations
3.1.5|AAA|Reading Level
3.1.6|AAA|Pronunciation
3.2.1|A|On Focus
3.2.2|A|On Input
3.2.3|AA|Consistent Navigation
3.2.4|AA|Consistent Identification
3.2.5|AAA|Change on Request
3.2.6|A|Consistent Help
3.3.1|A|Error Identification
3.3.2|A|Labels or Instructions
3.3.3|AA|Error Suggestion
3.3.4|AA|Error Prevention (Legal, Financial, Data)
3.3.5|AAA|Help
3.3.6|AAA|Error Prevention (All)
3.3.7|A|Redundant Entry
3.3.8|AA|Accessible Authentication (Minimum)
3.3.9|AAA|Accessible Authentication (Enhanced)
4.1.2|A|Name, Role, Value
4.1.3|AA|Status Messages
'''
CRITERIA = [dict(zip(('id','level','name'), line.split('|'))) for line in INVENTORY.strip().splitlines()]
GUIDANCE = {
 '1.1': 'Review every image, chart, equation, and object; add accurate alternatives or mark decorative content.',
 '1.2': 'If media exists, review captions, transcripts, audio description, and live-media alternatives.',
 '1.3': 'Check heading hierarchy, table header relationships, real lists, labels, reading order, and instructions independent of position or appearance.',
 '1.4': 'Review color-independent meaning, text/non-text contrast, zoom, reflow, text spacing, images of text, and media controls. Rendered checks are required.',
 '2.1': 'Test all interactive content with keyboard alone, including links, form fields, upload controls, and downloads; check traps and shortcuts.',
 '2.2': 'Check time limits, expiring downloads, pauses, authentication expiry, and whether users can retain their work.',
 '2.3': 'Inspect any animation/video for flashes and unnecessary motion.',
 '2.4': 'Check title, headings, descriptive links, navigation, tab order, and visible unobscured keyboard focus.',
 '2.5': 'Test accessible pointer alternatives, label matching, target sizes, motion controls, and drag alternatives in interactive content.',
 '3.1': 'Confirm document/default and passage languages; review jargon, abbreviations, readability, and pronunciation.',
 '3.2': 'Review predictable focus/input behavior, consistent navigation and help, and requested changes.',
 '3.3': 'Review form instructions, error messages, corrections, prevention of consequential errors, repeated entry, and authentication.',
 '4.1': 'Test exposed names, roles, states, values, and status announcements with assistive technology.',
}
PARTIAL = {'1.1.1','1.3.1','1.3.2','1.4.1','1.4.3','1.4.6','2.4.2','2.4.6','3.1.1'}


def framework_report():
    lines = ['\n\nFULL WCAG 2.2 REVIEW FRAMEWORK', 'Source: '+SOURCE, 'Non-web interpretation: '+ICT_SOURCE,
             'All 86 success criteria are listed, including AAA enhancement criteria. This inventory is not evidence that they were tested or passed.',
             'For each criterion, a reviewer must decide applicability to this document, its delivery context, and any interactive content. A/AA is the baseline review target; AAA is additional guidance.',
             'Word/PDF structure checks and automatic formatting cover only parts of some criteria. App UI checks do not establish accessibility of an uploaded document. No full conformance claim is made.']
    previous = None
    for item in CRITERIA:
        guideline = '.'.join(item['id'].split('.')[:2])
        if guideline != previous:
            lines.extend(['', 'GUIDELINE '+guideline+': '+GUIDANCE[guideline]])
            previous = guideline
        status = 'PARTIAL AUTOMATION — human verification required' if item['id'] in PARTIAL else 'NOT AUTOMATICALLY TESTED — applicability and human review required'
        lines.append(f"{item['id']} [{item['level']}] {item['name']}: {status}")
    return '\n'.join(lines)+'\n'
