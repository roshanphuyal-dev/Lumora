import { useState } from "react"
import { Check, Copy } from "lucide-react"
import { cn } from "@/lib/utils"

interface CodeBlockProps {
  className?: string
  children?: React.ReactNode
}

// rehype-highlight puts the language on the <code>'s className (language-xxx / hljs);
// react-markdown hands us the <pre><code> pair as a single "pre" element to render.
export function CodeBlock({ className, children }: CodeBlockProps) {
  const [copied, setCopied] = useState(false)

  async function handleCopy(event: React.MouseEvent<HTMLButtonElement>) {
    const codeEl = event.currentTarget.closest("figure")?.querySelector("code")
    const text = codeEl?.textContent ?? ""
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <figure className="group relative my-2">
      <button
        type="button"
        onClick={handleCopy}
        aria-label={copied ? "Copied" : "Copy code"}
        className="absolute top-1.5 right-1.5 z-10 flex items-center gap-1 rounded-md border
          border-border bg-background/80 px-1.5 py-1 text-xs text-muted-foreground opacity-0
          backdrop-blur transition-opacity group-hover:opacity-100 hover:text-foreground
          focus-visible:opacity-100"
      >
        {copied ? <Check className="size-3" aria-hidden="true" /> : <Copy className="size-3" aria-hidden="true" />}
      </button>
      <pre
        className={cn(
          "overflow-x-auto rounded-lg border border-border bg-muted/50 p-3 text-xs leading-relaxed",
          className,
        )}
      >
        {children}
      </pre>
    </figure>
  )
}
