// PDF export for the notebook chat. Renders from the already-rendered chat DOM
// (cloned message nodes), not from raw Markdown, so KaTeX/tables/code/images
// come through as they appear on screen (docs/adr/0009-ai-chat-streaming-persistence-export.md).
//
// jsPDF/html2canvas-pro are only ever loaded via dynamic import from the export
// button handler -- never part of the initial chat bundle.
//
// Rasterizes the container with html2canvas-pro into one tall canvas, then
// slices that canvas into A4-height image strips, one per page, via jsPDF's
// addImage -- rather than jsPDF's own `doc.html()` DOM-to-PDF conversion.
// `doc.html()` was tried first and rejected: its internal text-color
// resolution can't parse this app's oklch()-based Tailwind v4 tokens and
// fails *silently* (no thrown error), producing a PDF with correct
// extractable text but every bit of it invisible. Full-page rasterization
// sidesteps that pipeline entirely at the cost of the exported text not being
// selectable -- an acceptable tradeoff since the spec prioritizes visual
// fidelity (KaTeX/tables/code/images matching what's on screen) over that.
//
// Uses the `html2canvas-pro` fork, not `html2canvas`: stock html2canvas's
// color parser throws outright on oklch() ("Attempting to parse an
// unsupported color function 'oklch'"), crashing export before any canvas is
// produced.

const A4_WIDTH_MM = 210
const A4_HEIGHT_MM = 297
const MARGIN_MM = 15
const HEADER_MM = 22
const FOOTER_MM = 16
const CONTENT_WINDOW_PX = 720 // ~190mm at 96dpi, matches A4 width minus margins
const RENDER_SCALE = 2 // devicePixelRatio-equivalent for crisp text/code in the raster

export interface ExportChatToPdfOptions {
  title: string
  messageElements: HTMLElement[]
}

export async function exportChatToPdf({ title, messageElements }: ExportChatToPdfOptions): Promise<void> {
  if (messageElements.length === 0) return

  const { jsPDF } = await import("jspdf")
  const html2canvas = (await import("html2canvas-pro")).default

  const doc = new jsPDF({ unit: "mm", format: "a4" })
  const contentWidthMm = A4_WIDTH_MM - MARGIN_MM * 2
  const exportDate = new Date().toLocaleString()

  const container = buildExportContainer(messageElements)
  document.body.appendChild(container)

  try {
    const canvas = await html2canvas(container, {
      scale: RENDER_SCALE,
      backgroundColor: "#ffffff",
      useCORS: true,
    })

    const pxPerMm = canvas.width / contentWidthMm
    const pageContentHeightMm = A4_HEIGHT_MM - HEADER_MM - FOOTER_MM
    const pageContentHeightPx = Math.floor(pageContentHeightMm * pxPerMm)
    const totalPages = Math.max(1, Math.ceil(canvas.height / pageContentHeightPx))

    for (let page = 0; page < totalPages; page++) {
      if (page > 0) doc.addPage()

      const sliceHeightPx = Math.min(pageContentHeightPx, canvas.height - page * pageContentHeightPx)
      const sliceCanvas = document.createElement("canvas")
      sliceCanvas.width = canvas.width
      sliceCanvas.height = sliceHeightPx
      const ctx = sliceCanvas.getContext("2d")
      if (!ctx) throw new Error("Could not get 2D context for PDF page slice")
      ctx.drawImage(canvas, 0, page * pageContentHeightPx, canvas.width, sliceHeightPx, 0, 0, canvas.width, sliceHeightPx)

      // JPEG, not PNG: a full-resolution PNG of a tall chat conversation runs
      // into multiple MB per page (verified: ~5MB for a single short message
      // at scale 2). Quality 0.85 keeps text/code legible while keeping the
      // file a reasonable size for longer conversations.
      doc.addImage(
        sliceCanvas.toDataURL("image/jpeg", 0.85),
        "JPEG",
        MARGIN_MM,
        HEADER_MM,
        contentWidthMm,
        sliceHeightPx / pxPerMm,
      )

      drawHeader(doc, title, exportDate)
      drawFooter(doc, page + 1, totalPages)
    }

    doc.save(`${sanitizeFilename(title)}-chat-export.pdf`)
  } finally {
    document.body.removeChild(container)
  }
}

function buildExportContainer(messageElements: HTMLElement[]): HTMLDivElement {
  const container = document.createElement("div")
  // Kept at valid in-flow coordinates (0,0) rather than shifted far
  // off-screen (e.g. left: -10000px): html2canvas-pro renders reliably here,
  // hidden from the user behind the real page via a negative z-index instead.
  container.style.position = "absolute"
  container.style.top = "0"
  container.style.left = "0"
  container.style.zIndex = "-1"
  container.style.width = `${CONTENT_WINDOW_PX}px`
  container.style.background = "#ffffff"
  container.style.color = "#0a0a0a"
  container.style.fontFamily = "Inter, system-ui, sans-serif"

  // This app's Tailwind v4 tokens (frontend/src/index.css) are oklch()
  // custom properties. html2canvas-pro parses oklch() fine, but overriding
  // them here with plain hex keeps the raster's colors close to a light-mode
  // reading of the app regardless of which theme the viewer currently has
  // active (the export is always rendered on a white page).
  const colorOverrides: Record<string, string> = {
    "--background": "#ffffff",
    "--foreground": "#0a0a0a",
    "--card": "#ffffff",
    "--card-foreground": "#0a0a0a",
    "--muted": "#f5f5f5",
    "--muted-foreground": "#737373",
    "--border": "#e5e5e5",
    "--primary": "#059669",
    "--primary-foreground": "#fafafa",
  }
  for (const [property, value] of Object.entries(colorOverrides)) {
    container.style.setProperty(property, value)
  }

  for (const el of messageElements) {
    const clone = el.cloneNode(true) as HTMLElement
    clone.style.marginBottom = "14px"
    clone.style.border = "1px solid #e5e5e5"
    clone.style.borderRadius = "8px"
    clone.style.padding = "12px"
    clone.querySelectorAll('button, [role="checkbox"]').forEach((node) => node.remove())
    container.appendChild(clone)
  }

  return container
}

function drawHeader(doc: import("jspdf").jsPDF, title: string, exportDate: string) {
  doc.setFontSize(9)
  doc.setTextColor(120)
  doc.text("AI CHAT EXPORT", MARGIN_MM, 9)
  doc.text(`Conversation: ${title}`, MARGIN_MM, 13.5)
  doc.text(`Exported: ${exportDate}`, A4_WIDTH_MM - MARGIN_MM, 9, { align: "right" })
  doc.setDrawColor(220)
  doc.line(MARGIN_MM, 16, A4_WIDTH_MM - MARGIN_MM, 16)
}

function drawFooter(doc: import("jspdf").jsPDF, pageNumber: number, totalPages: number) {
  doc.setFontSize(8)
  doc.setTextColor(150)
  doc.text(`Page ${pageNumber} of ${totalPages}`, A4_WIDTH_MM - MARGIN_MM, A4_HEIGHT_MM - 8, { align: "right" })
}

function sanitizeFilename(name: string): string {
  const slug = name
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "")
  return slug || "notebook"
}
