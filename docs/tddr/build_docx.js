const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell,
  WidthType, ImageRun, BorderStyle, ShadingType, AlignmentType, PageBreak
} = require('docx');

const DIR = __dirname;
const mdPath = path.join(DIR, 'TDDR_UPAO-MAS-EDU.md');
const md = fs.readFileSync(mdPath, 'utf8');
const lines = md.split(/\r?\n/);

const PAGE_WIDTH_DXA = 11906; // A4
const MARGIN_DXA = 1440;
const USABLE_WIDTH_DXA = PAGE_WIDTH_DXA - 2 * MARGIN_DXA;

const FIGURE_MAP = {
  'Figura 1.': 'upao_arquitectura_fig1.png',
  'Figura 2.': 'fig2_casos_de_uso.png',
  'Figura 3.': 'fig3_modelo_er.png',
  'Figura 4.': 'fig4_secuencia_orquestacion_modulo.png',
  'Figura 5.': 'fig5_wireframes.png',
};
const insertedFigures = new Set();

function imageDims(file) {
  // returns [width, height] in px, scaled to max width 600
  const dims = {
    'upao_arquitectura_fig1.png': [1040, 830],
    'fig2_casos_de_uso.png': [1000, 680],
    'fig3_modelo_er.png': [1180, 900],
    'fig4_secuencia_orquestacion_modulo.png': [1080, 620],
    'fig5_wireframes.png': [1200, 780],
  };
  const [w, h] = dims[file];
  const targetW = 600;
  const targetH = Math.round(targetW * h / w);
  return [targetW, targetH];
}

// ---- inline formatting parser: **bold**, `code`, plain ----
function parseInline(text) {
  const runs = [];
  // tokenize by ** and ` boundaries
  const tokenRe = /(\*\*.+?\*\*|`.+?`|\*[^*\n]+?\*)/g;
  let lastIndex = 0;
  let m;
  while ((m = tokenRe.exec(text)) !== null) {
    if (m.index > lastIndex) {
      runs.push(new TextRun({ text: text.slice(lastIndex, m.index) }));
    }
    const tok = m[0];
    if (tok.startsWith('**')) {
      runs.push(new TextRun({ text: tok.slice(2, -2), bold: true }));
    } else if (tok.startsWith('`')) {
      runs.push(new TextRun({ text: tok.slice(1, -1), font: 'Consolas', shading: { type: ShadingType.CLEAR, fill: 'F0F0F0' } }));
    } else if (tok.startsWith('*')) {
      runs.push(new TextRun({ text: tok.slice(1, -1), italics: true }));
    }
    lastIndex = tokenRe.lastIndex;
  }
  if (lastIndex < text.length) {
    runs.push(new TextRun({ text: text.slice(lastIndex) }));
  }
  if (runs.length === 0) runs.push(new TextRun({ text: '' }));
  return runs;
}

function cellParagraph(text, opts) {
  return new Paragraph({ children: parseInline(text), spacing: { after: 40 }, ...opts });
}

function makeCell(text, width, header) {
  return new TableCell({
    width: { size: width, type: WidthType.DXA },
    shading: header ? { type: ShadingType.CLEAR, fill: 'D9E2F3' } : undefined,
    margins: { top: 60, bottom: 60, left: 80, right: 80 },
    children: [cellParagraph(text, header ? { children: [new TextRun({ text, bold: true })] } : undefined)].filter(Boolean).length
      ? [new Paragraph({ children: header ? [new TextRun({ text, bold: true, size: 18 })] : parseInline(text).map(r => r), spacing: { after: 20 } })]
      : [],
  });
}

function splitTableRow(line) {
  let s = line.trim();
  if (s.startsWith('|')) s = s.slice(1);
  if (s.endsWith('|')) s = s.slice(0, -1);
  return s.split('|').map(c => c.trim());
}

function isSepRow(line) {
  const s = line.trim();
  return /^\|?[\s:\-|]+\|?$/.test(s) && s.includes('-');
}

const children = [];

let i = 0;
while (i < lines.length) {
  const raw = lines[i];
  const line = raw;

  if (line.trim() === '') { i++; continue; }
  if (line.trim() === '---') { i++; continue; }

  // fenced code block
  if (line.trim().startsWith('```')) {
    i++;
    const codeLines = [];
    while (i < lines.length && !lines[i].trim().startsWith('```')) {
      codeLines.push(lines[i]);
      i++;
    }
    i++; // skip closing fence
    codeLines.forEach(cl => {
      children.push(new Paragraph({
        children: [new TextRun({ text: cl.length ? cl : ' ', font: 'Consolas', size: 18 })],
        shading: { type: ShadingType.CLEAR, fill: 'F5F5F5' },
        spacing: { after: 0 },
      }));
    });
    children.push(new Paragraph({ text: '', spacing: { after: 100 } }));
    continue;
  }

  // heading
  const hMatch = line.match(/^(#{1,4})\s+(.*)$/);
  if (hMatch) {
    const level = hMatch[1].length;
    const text = hMatch[2].trim();
    if (level === 1) {
      children.push(new Paragraph({ text, heading: HeadingLevel.TITLE, spacing: { after: 200 } }));
    } else {
      if (level === 2) {
        children.push(new Paragraph({ children: [new PageBreak()] }));
      }
      const map = { 2: HeadingLevel.HEADING_1, 3: HeadingLevel.HEADING_2, 4: HeadingLevel.HEADING_3 };
      children.push(new Paragraph({ text, heading: map[level], spacing: { before: 200, after: 120 } }));
    }
    i++;
    continue;
  }

  // table
  if (line.trim().startsWith('|')) {
    const tableLines = [];
    let j = i;
    while (j < lines.length && lines[j].trim().startsWith('|')) {
      tableLines.push(lines[j]);
      j++;
    }
    // remove separator row (should be index 1)
    const headerCells = splitTableRow(tableLines[0]);
    const bodyLines = tableLines.slice(1).filter(l => !isSepRow(l));
    const numCols = headerCells.length;
    const colWidth = Math.floor(USABLE_WIDTH_DXA / numCols);
    const colWidths = new Array(numCols).fill(colWidth);

    const rows = [];
    rows.push(new TableRow({
      children: headerCells.map((c, idx) => makeCell(c, colWidths[idx], true)),
      tableHeader: true,
    }));
    bodyLines.forEach(bl => {
      const cells = splitTableRow(bl);
      while (cells.length < numCols) cells.push('');
      rows.push(new TableRow({
        children: cells.slice(0, numCols).map((c, idx) => makeCell(c, colWidths[idx], false)),
      }));
    });

    children.push(new Table({
      width: { size: USABLE_WIDTH_DXA, type: WidthType.DXA },
      columnWidths: colWidths,
      rows,
    }));
    children.push(new Paragraph({ text: '', spacing: { after: 160 } }));
    i = j;
    continue;
  }

  // bullet list
  const bulletMatch = line.match(/^\s*-\s+(.*)$/);
  if (bulletMatch) {
    children.push(new Paragraph({
      children: parseInline(bulletMatch[1]),
      bullet: { level: 0 },
      spacing: { after: 60 },
    }));
    i++;
    continue;
  }

  // numbered list (rendered as plain paragraph with leading number, already explicit in source)
  const numMatch = line.match(/^\s*(\d+)\.\s+(.*)$/);
  if (numMatch) {
    children.push(new Paragraph({
      children: [new TextRun({ text: numMatch[1] + '. ', bold: false }), ...parseInline(numMatch[2])],
      spacing: { after: 60 },
      indent: { left: 260 },
    }));
    i++;
    continue;
  }

  // regular paragraph
  const para = new Paragraph({ children: parseInline(line), spacing: { after: 120 } });
  children.push(para);

  // figure insertion after a "**Figura N.**" caption paragraph
  for (const key of Object.keys(FIGURE_MAP)) {
    if (line.includes(key) && !insertedFigures.has(key)) {
      insertedFigures.add(key);
      const file = FIGURE_MAP[key];
      const [w, h] = imageDims(file);
      const imgData = fs.readFileSync(path.join(DIR, file));
      children.push(new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [new ImageRun({ data: imgData, transformation: { width: w, height: h }, type: 'png' })],
        spacing: { after: 200 },
      }));
      break;
    }
  }

  i++;
}

const doc = new Document({
  sections: [{
    properties: {
      page: {
        size: { width: PAGE_WIDTH_DXA, height: 16838 },
        margin: { top: MARGIN_DXA, bottom: MARGIN_DXA, left: MARGIN_DXA, right: MARGIN_DXA },
      },
    },
    children,
  }],
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(path.join(DIR, 'TDDR_UPAO-MAS-EDU.docx'), buf);
  console.log('DOCX written:', buf.length, 'bytes');
});
