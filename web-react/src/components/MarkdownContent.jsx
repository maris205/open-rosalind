import ReactMarkdown from 'react-markdown';
import remarkBreaks from 'remark-breaks';
import remarkGfm from 'remark-gfm';

const EVIDENCE_SECTION_RE = /(?:^|\n+)#{2,6}\s+Evidence\s*\n[\s\S]*$/i;

export function cleanSummary(md) {
  if (!md) return '';
  let text = String(md).replace(/\r\n?/g, '\n').trim();
  if (text.includes('\\n') && !text.includes('\n')) {
    text = text.replace(/\\n/g, '\n').trim();
  }
  return text.replace(EVIDENCE_SECTION_RE, '').trimEnd();
}

function stripInlineMarkdown(text) {
  return String(text || '')
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '$1')
    .replace(/[*_`~]/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

export function extractLeadSummary(md, max = 220) {
  const cleaned = cleanSummary(md);
  if (!cleaned) return '';

  const paragraphs = cleaned
    .split(/\n\s*\n/)
    .map((part) => part.trim())
    .filter(Boolean);

  const preferred = paragraphs.find((part) => {
    const firstLine = part.split('\n')[0]?.trim() || '';
    return firstLine && !firstLine.startsWith('|') && !firstLine.startsWith('##');
  }) || paragraphs[0] || '';

  const firstLine = preferred
    .split('\n')
    .map((line) => line.trim())
    .find((line) => line && !line.startsWith('|') && !line.startsWith('##')) || '';

  const compact = stripInlineMarkdown(firstLine);
  if (!compact) return '';
  return compact.length > max ? `${compact.slice(0, max - 1)}…` : compact;
}

function ExternalLink(props) {
  const href = String(props.href || '');
  const isInternalAnchor = href.startsWith('#');
  return (
    <a
      {...props}
      target={isInternalAnchor ? undefined : '_blank'}
      rel={isInternalAnchor ? undefined : 'noreferrer noopener'}
    />
  );
}

function MarkdownTable({ children }) {
  return (
    <div className="markdown-table-wrap">
      <table>{children}</table>
    </div>
  );
}

export default function MarkdownContent({ content, className = '' }) {
  const cleaned = cleanSummary(content);
  if (!cleaned) return null;

  return (
    <div className={className ? `markdown ${className}` : 'markdown'}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkBreaks]}
        components={{
          a: ExternalLink,
          table: MarkdownTable,
        }}
      >
        {cleaned}
      </ReactMarkdown>
    </div>
  );
}
