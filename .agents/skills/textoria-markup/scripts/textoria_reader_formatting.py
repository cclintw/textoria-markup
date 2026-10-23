"""Render note spans and pipe tables while retaining canonical source offsets."""
import html
import re

NOTE = re.compile(r'<span class="note">|</span>')


def formatted_paragraph(para, data, render_content):
    text = ''.join(node['text'] for node in para['content'])
    table = re.match(r'^\|.*\|\n\|[ :|\-]+\|(?:\n|$)', text)
    if not table and '<span class="note">' not in text:
        return None
    nodes = []
    cursor = 0
    for node in para['content']:
        nodes.append((cursor, cursor + len(node['text']), node))
        cursor += len(node['text'])

    def mapped(value, start, end, rendered=None):
        return (f'<span data-source-start="{start}" data-source-end="{end}">'
                + (html.escape(value) if rendered is None else rendered) + '</span>')

    def inline(start, end):
        result = []
        for left, right, node in nodes:
            a, b = max(start, left), min(end, right)
            if a >= b:
                continue
            value = text[a:b]
            if node.get('annotation') and a == left and b == right:
                rendered = render_content({**para, 'content': [node]}, data)
                result.append(mapped(value, a, b, rendered))
                continue
            cursor = a
            for match in NOTE.finditer(value):
                x, y = a + match.start(), a + match.end()
                if cursor < x:
                    result.append(mapped(text[cursor:x], cursor, x))
                result.append(match.group())
                cursor = y
            if cursor < b:
                result.append(mapped(text[cursor:b], cursor, b))
        return ''.join(result)

    attrs = f'id="{para["paragraph_id"]}" data-paragraph-number="{para["paragraph_index"]}"'
    if not table:
        return f'<p {attrs}>{inline(0, len(text))}</p>'
    rows = []
    offset = 0
    for index, line in enumerate(text.splitlines(keepends=True)):
        if index != 1:
            cells = []
            pipes = [m.start() for m in re.finditer(r'(?<!\\)\|', line)]
            for a, b in zip(pipes, pipes[1:]):
                raw = line[a + 1:b]
                first = offset + a + 1 + len(raw) - len(raw.lstrip())
                last = offset + b - len(raw) + len(raw.rstrip())
                tag = 'th' if index == 0 else 'td'
                cells.append(f'<{tag}>' + inline(first, last) + f'</{tag}>')
            rows.append('<tr>' + ''.join(cells) + '</tr>')
        offset += len(line)
    return (f'<div class="formatted-paragraph" {attrs}><table class="source-table">'
            + '<thead>' + rows[0] + '</thead><tbody>' + ''.join(rows[1:])
            + '</tbody></table></div>')
