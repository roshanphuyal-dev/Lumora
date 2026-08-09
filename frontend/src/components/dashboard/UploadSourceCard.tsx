import { useRef } from "react"
import { UploadCloud } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { ApiError } from "@/lib/api"
import { useUploadSource, type UploadStage } from "@/hooks/use-upload-source"

const STAGE_LABEL: Record<UploadStage, string> = {
  uploading: "Uploading…",
  parsing: "Reading your file…",
  "creating-notebook": "Creating your notebook…",
}

const ACCEPTED_TYPES =
  ".pdf,.docx,.pptx,.png,.jpg,.jpeg,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.openxmlformats-officedocument.presentationml.presentation,image/png,image/jpeg"

export function UploadSourceCard() {
  const inputRef = useRef<HTMLInputElement>(null)
  const { uploadSource, stage, isError, error, reset } = useUploadSource()
  const isBusy = stage !== null

  function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = ""
    if (file) uploadSource(file)
  }

  return (
    <Card className="border-dashed">
      <CardContent className="flex flex-col items-center gap-3 py-10 text-center">
        <UploadCloud className="size-8 text-primary" aria-hidden="true" />
        <div className="flex flex-col gap-1">
          <p className="text-sm font-medium text-foreground">Add your first source</p>
          <p className="text-xs text-muted-foreground">PDF, DOCX, PPTX, or images</p>
        </div>

        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED_TYPES}
          className="sr-only"
          onChange={handleFileChange}
        />
        <Button onClick={() => inputRef.current?.click()} disabled={isBusy}>
          {isBusy ? STAGE_LABEL[stage] : "Upload material"}
        </Button>

        {isError && (
          <div className="flex flex-col items-center gap-1">
            <p className="text-xs text-destructive" role="alert">
              {error instanceof ApiError || error instanceof Error
                ? error.message
                : "Something went wrong."}
            </p>
            <button
              type="button"
              onClick={reset}
              className="text-xs font-medium text-primary hover:underline"
            >
              Try again
            </button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
