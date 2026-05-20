"""
Run once to generate questions_data.json from docx files.
Usage: python parse_questions.py
"""
import sys, json, re
sys.stdout.reconfigure(encoding='utf-8')
from docx import Document

DOCX_FILES = [
    (r"C:\Users\15348\Desktop\比赛\创新杯\题库\地震题目带答案.docx", "地震"),
    (r"C:\Users\15348\Desktop\比赛\创新杯\题库\测井题目带答案.docx", "测井"),
]

SKIP_PATTERNS = [
    '地球物理知识竞赛', '创新杯', '题目汇编', '知识竞赛',
]

SECTION_PATTERNS = ['填空题', '选择题', '判断题', '简答题']


def is_skip(text):
    return any(kw in text for kw in SKIP_PATTERNS)


def get_section_type(section):
    if '填空题' in section:
        return 'fill'
    if '选择题' in section:
        return 'choice'
    if '判断题' in section:
        return 'judge'
    return 'other'


def clean_answer(raw):
    raw = re.sub(r'【答案】|答案[:：]?\s*', '', raw).strip()
    # Remove leading dashes, semicolons used as separators
    raw = raw.strip('；;—')
    return raw.strip()


def parse_options_from_line(text):
    """Extract A/B/C/D options from a single line like 'A. foo  B. bar  C. baz'"""
    pattern = r'([A-D])[\.、\)）]\s*([^A-D（【\n]{1,60}?)(?=\s+[A-D][\.、\)）]|$)'
    matches = re.findall(pattern, text)
    if matches:
        return [f"{k}. {v.strip()}" for k, v in matches]
    return []


def parse_file(filepath, category):
    doc = Document(filepath)
    paras = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

    questions = []
    section = ''
    i = 0

    while i < len(paras):
        p = paras[i]

        if is_skip(p):
            i += 1
            continue

        # Section header
        if any(kw in p for kw in SECTION_PATTERNS):
            section = p
            i += 1
            continue

        # Question start: "N. text" or "N、text"
        q_match = re.match(r'^(\d+)[\.、。]\s*(.+)', p)
        if not q_match or '答案' in p:
            i += 1
            continue

        q_text = q_match.group(2).strip()
        opts = []
        answer = ''
        j = i + 1

        while j < len(paras):
            nxt = paras[j]

            if '答案' in nxt:
                answer = clean_answer(nxt)
                j += 1
                break

            # Pure option line: starts with A. or A) etc.
            if re.match(r'^[A-D][\.、\)）]\s*\S', nxt):
                opts.append(nxt.strip())
                j += 1
                continue

            # Options embedded in a line like "A. foo  B. bar"
            embedded = parse_options_from_line(nxt)
            if len(embedded) >= 2:
                opts.extend(embedded)
                j += 1
                continue

            # Next question starts → stop
            if re.match(r'^\d+[\.、。]\s*', nxt):
                break

            # Section header → stop
            if any(kw in nxt for kw in SECTION_PATTERNS):
                break

            # Continuation of question text
            q_text += ' ' + nxt
            j += 1

        i = j

        # If no opts yet, try to extract from question text itself
        if not opts and get_section_type(section) == 'choice':
            # Try "A. x  B. y  C. z  D. w" pattern inside q_text
            embedded = parse_options_from_line(q_text)
            if len(embedded) >= 2:
                # Strip opts from question stem
                stem_end = re.search(r'\s+A[\.、\)）]', q_text)
                if stem_end:
                    q_text = q_text[:stem_end.start()].strip()
                opts = embedded

        # Normalize opts: ensure "A. text" format
        normalized_opts = []
        for opt in opts:
            opt = opt.strip()
            m = re.match(r'^([A-D])[\.、\)）\s]+(.+)', opt)
            if m:
                normalized_opts.append(f"{m.group(1)}. {m.group(2).strip()}")
            else:
                normalized_opts.append(opt)

        questions.append({
            'id': len(questions) + 1,
            'category': category,
            'type': get_section_type(section),
            'section': section,
            'q': q_text.strip(),
            'opts': normalized_opts,
            'a': answer,
        })

    return questions


def main():
    all_questions = []
    for filepath, category in DOCX_FILES:
        qs = parse_file(filepath, category)
        print(f"{category}: {len(qs)} questions parsed")
        # Reassign global IDs
        for q in qs:
            q['id'] = len(all_questions) + q['id']
        # Fix: re-assign after accumulation
        offset = len(all_questions)
        for q in qs:
            q['id'] = offset + qs.index(q) + 1
        all_questions.extend(qs)

    # Final global ID assignment
    for idx, q in enumerate(all_questions):
        q['id'] = idx + 1

    output = {str(q['id']): q for q in all_questions}
    with open('questions_data.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Total: {len(all_questions)} questions → questions_data.json")

    # Quick stats
    from collections import Counter
    types = Counter(q['type'] for q in all_questions)
    cats = Counter(q['category'] for q in all_questions)
    print("Types:", dict(types))
    print("Categories:", dict(cats))


if __name__ == '__main__':
    main()
