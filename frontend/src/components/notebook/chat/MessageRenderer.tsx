import { memo } from "react"
import Markdown, { type Components } from "react-markdown"
import "katex/dist/katex.min.css"
import remarkGfm from "remark-gfm"
import remarkMath from "remark-math"
import rehypeKatex from "rehype-katex"
import rehypeHighlight from "rehype-highlight"
import rehypeSanitize, { defaultSchema } from "rehype-sanitize"
import { CodeBlock } from "@/components/notebook/chat/CodeBlock"

// Extends the default (GitHub-flavored) sanitize schema so KaTeX's generated
// markup (class/style-heavy spans + MathML) and rehype-highlight's per-token
// `hljs-*` span classes survive sanitization -- both run upstream of this
// schema and are trusted output of those libraries, not raw AI text.
const sanitizeSchema = structuredClone(defaultSchema)
sanitizeSchema.attributes = {
  ...sanitizeSchema.attributes,
  span: [...(sanitizeSchema.attributes?.span ?? []), "className", "style"],
  div: [...(sanitizeSchema.attributes?.div ?? []), "className", "style"],
  code: [...(sanitizeSchema.attributes?.code ?? []), "className"],
  svg: [...(sanitizeSchema.attributes?.svg ?? []), "viewBox", "preserveAspectRatio", "width", "height", "style"],
  path: ["d"],
  line: ["x1", "x2", "y1", "y2"],
  annotation: ["encoding"],
}
sanitizeSchema.tagNames = [
  ...(sanitizeSchema.tagNames ?? []),
  "math",
  "mi",
  "mo",
  "mn",
  "msup",
  "msub",
  "msubsup",
  "mfrac",
  "mrow",
  "mspace",
  "mtext",
  "munderover",
  "munder",
  "mover",
  "msqrt",
  "mroot",
  "semantics",
  "annotation",
  "mtable",
  "mtr",
  "mtd",
  "mpadded",
  "mphantom",
  "svg",
  "path",
  "line",
]

const remarkPlugins = [remarkGfm, remarkMath]
const rehypePlugins = [rehypeKatex, rehypeHighlight, [rehypeSanitize, sanitizeSchema]] as const

const components: Components = {
  pre({ children }) {
    return <CodeBlock>{children}</CodeBlock>
  },
  code({ className, children, ...props }) {
    // rehype-highlight only touches <code> inside <pre> (fenced blocks) and
    // always assigns it a className (at least "hljs"); inline code has none.
    if (!className) {
      return (
        <code className="rounded bg-muted px-1 py-0.5 text-xs" {...props}>
          {children}
        </code>
      )
    }
    return (
      <code className={className} {...props}>
        {children}
      </code>
    )
  },
  img({ src, alt }) {
    if (!src) return null
    return (
      <img
        src={src}
        alt={alt ?? ""}
        loading="lazy"
        referrerPolicy="no-referrer"
        className="my-2 max-w-full rounded-lg border border-border"
      />
    )
  },
  a({ href, children }) {
    return (
      <a href={href} target="_blank" rel="noopener noreferrer nofollow" className="underline underline-offset-2">
        {children}
      </a>
    )
  },
}

interface MessageRendererProps {
  content: string
}

// Memoized on content alone: a message's rendered output never changes once
// its content string is stable, so this skips re-parsing Markdown/re-rendering
// KaTeX for every sibling message when only the latest message updates.
export const MessageRenderer = memo(function MessageRenderer({ content }: MessageRendererProps) {
  return (
    <div
      className="min-w-0 text-sm leading-relaxed text-foreground
        [&_h1]:mt-3 [&_h1]:mb-1 [&_h1]:text-base [&_h1]:font-semibold [&_h1]:first:mt-0
        [&_h2]:mt-3 [&_h2]:mb-1 [&_h2]:text-sm [&_h2]:font-semibold [&_h2]:first:mt-0
        [&_h3]:mt-2 [&_h3]:mb-1 [&_h3]:text-sm [&_h3]:font-medium
        [&_p]:mb-2 [&_p]:last:mb-0
        [&_strong]:font-semibold
        [&_ul]:mb-2 [&_ul]:list-disc [&_ul]:pl-5
        [&_ol]:mb-2 [&_ol]:list-decimal [&_ol]:pl-5
        [&_li]:mb-0.5
        [&_blockquote]:mb-2 [&_blockquote]:border-l-2 [&_blockquote]:border-border [&_blockquote]:pl-3 [&_blockquote]:text-muted-foreground
        [&_table]:mb-2 [&_table]:w-full [&_table]:overflow-x-auto [&_table]:text-xs
        [&_th]:border-b [&_th]:border-border [&_th]:py-1 [&_th]:text-left [&_th]:font-medium
        [&_td]:border-b [&_td]:border-border [&_td]:py-1
        [&_.katex-display]:overflow-x-auto [&_.katex-display]:py-1
        [&_.hljs-keyword]:text-purple-600 [&_.hljs-keyword]:dark:text-purple-400
        [&_.hljs-string]:text-emerald-700 [&_.hljs-string]:dark:text-emerald-400
        [&_.hljs-number]:text-amber-700 [&_.hljs-number]:dark:text-amber-400
        [&_.hljs-comment]:text-muted-foreground [&_.hljs-comment]:italic
        [&_.hljs-title]:text-blue-700 [&_.hljs-title]:dark:text-blue-400
        [&_.hljs-function_]:text-blue-700 [&_.hljs-function_]:dark:text-blue-400
        [&_.hljs-attr]:text-amber-700 [&_.hljs-attr]:dark:text-amber-400
        [&_.hljs-built_in]:text-purple-600 [&_.hljs-built_in]:dark:text-purple-400
        [&_.hljs-literal]:text-amber-700 [&_.hljs-literal]:dark:text-amber-400
        [&_.hljs-tag]:text-purple-600 [&_.hljs-tag]:dark:text-purple-400"
    >
      <Markdown remarkPlugins={remarkPlugins} rehypePlugins={rehypePlugins} components={components}>
        {content}
      </Markdown>
    </div>
  )
})
