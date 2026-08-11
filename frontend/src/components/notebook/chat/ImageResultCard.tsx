import { Card, CardFooter } from "@/components/ui/card"

interface ImageResultCardProps {
  imageUrl: string
  attribution: string | null
  license: string | null
  sourceUrl: string | null
  alt: string
}

// docs/adr/0010: Wikimedia Commons/Openverse content is CC-family licensed and requires
// visible attribution wherever it's shown -- rendered in CardFooter as readable text (not
// a muted footnote), per the ADR's explicit callout and .claude/rules/ui.md's WCAG AA
// contrast requirement for new UI.
export function ImageResultCard({ imageUrl, attribution, license, sourceUrl, alt }: ImageResultCardProps) {
  return (
    <Card size="sm" className="mt-2 max-w-sm">
      <img src={imageUrl} alt={alt} className="max-h-64 w-full object-contain" loading="lazy" />
      <CardFooter className="flex-col items-start gap-1.5">
        {attribution && <p className="text-sm text-foreground">{attribution}</p>}
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs">
          {license && <span className="font-medium text-foreground">{license}</span>}
          {sourceUrl && (
            <a
              href={sourceUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary underline-offset-2 hover:underline"
            >
              View source
            </a>
          )}
        </div>
      </CardFooter>
    </Card>
  )
}
