import { getDocument, type DocumentDetail } from "@/lib/documents"

const POLL_INTERVAL_MS = 1500
const POLL_TIMEOUT_MS = 90_000

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

// Parsing has no byte-level signal to report (unlike upload), so progress is
// derived from elapsed time against the poll timeout -- capped below 100 so
// the bar never claims "done" before parse_status actually says so.
export async function waitForParse(
  documentId: string,
  onProgress: (percent: number) => void
): Promise<DocumentDetail> {
  const startedAt = Date.now()
  const deadline = startedAt + POLL_TIMEOUT_MS
  for (;;) {
    const document = await getDocument(documentId)
    if (document.parse_status === "done") return document
    if (document.parse_status === "failed") {
      throw new Error(
        `Couldn't read "${document.title ?? document.filename}" — the file may be corrupted or unsupported.`
      )
    }
    if (Date.now() > deadline) {
      throw new Error(
        `Parsing "${document.title ?? document.filename}" is taking longer than expected. Try again shortly.`
      )
    }
    onProgress(Math.min(95, ((Date.now() - startedAt) / POLL_TIMEOUT_MS) * 100))
    await sleep(POLL_INTERVAL_MS)
  }
}
