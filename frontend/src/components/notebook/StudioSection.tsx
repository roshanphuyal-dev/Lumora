import { useEffect, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import {
  AudioWaveform,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  Download,
  FileText,
  GitBranch,
  Image,
  Loader2,
  Presentation,
  Table2,
  Trash2,
  XCircle,
} from "lucide-react"
import { useForm, type UseFormRegisterReturn } from "react-hook-form"
import Markdown from "react-markdown"
import rehypeSanitize from "rehype-sanitize"
import remarkGfm from "remark-gfm"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"
import { Textarea } from "@/components/ui/textarea"
import {
  useCreateGeneratedMaterial,
  useDeleteGeneratedMaterial,
  useGeneratedMaterials,
} from "@/hooks/use-studio"
import { ApiError } from "@/lib/api"
import {
  downloadGeneratedMaterial,
  getGeneratedMaterialBlob,
  type ArtifactType,
  type GeneratedMaterialCreate,
  type GeneratedMaterialRead,
  type GeneratedMaterialStatus,
} from "@/lib/studio"

const TYPE_META = {
  audio: { label: "Audio Overview", description: "A narrated discussion of the key ideas.", icon: AudioWaveform },
  report: { label: "Report", description: "A structured, readable document grounded in your sources.", icon: FileText },
  slides: { label: "Slide Deck", description: "A presentation-ready PDF for teaching or review.", icon: Presentation },
  infographic: { label: "Infographic", description: "A visual summary of concepts and relationships.", icon: Image },
  mindmap: { label: "Mind Map", description: "An expandable tree connecting the notebook's main ideas.", icon: GitBranch },
  data_table: { label: "Data Table", description: "A CSV extracting specific facts into rows and columns.", icon: Table2 },
} satisfies Record<ArtifactType, { label: string; description: string; icon: typeof FileText }>

const STATUS_META: Record<GeneratedMaterialStatus, { icon: typeof Clock; label: string; className: string }> = {
  pending: { icon: Clock, label: "Pending", className: "text-muted-foreground" },
  generating: { icon: Loader2, label: "Generating", className: "text-amber-700 dark:text-amber-400" },
  done: { icon: CheckCircle2, label: "Done", className: "text-success" },
  failed: { icon: XCircle, label: "Failed", className: "text-destructive" },
}

const SELECT_CLASS = "h-8 w-full rounded-lg border border-input bg-background px-2.5 text-sm text-foreground outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"

interface StudioFormValues {
  title: string
  format: string
  length: string
  focus: string
  prompt: string
  orientation: string
  detail: string
  description: string
}

interface MindMapNode {
  name: string
  children?: MindMapNode[]
}

function errorMessage(error: unknown, fallback: string) {
  return error instanceof ApiError ? error.message : fallback
}

function filenameFor(material: GeneratedMaterialRead) {
  const base = material.title.trim().replace(/[^a-z0-9]+/gi, "-").replace(/(^-|-$)/g, "") || "studio-material"
  const extensions: Partial<Record<ArtifactType, string>> = {
    audio: "mp3",
    slides: "pdf",
    infographic: "png",
    data_table: "csv",
  }
  const extension = extensions[material.artifact_type]
  return extension ? `${base}.${extension}` : base
}

function MindMapBranch({ node }: { node: MindMapNode }) {
  const [open, setOpen] = useState(true)
  const hasChildren = Boolean(node.children?.length)

  return (
    <li>
      <div className="flex items-center gap-1.5 py-1">
        {hasChildren ? (
          <button
            type="button"
            aria-expanded={open}
            aria-label={`${open ? "Collapse" : "Expand"} ${node.name}`}
            onClick={() => setOpen((value) => !value)}
            className="rounded p-0.5 text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            {open ? <ChevronDown className="size-3.5" /> : <ChevronRight className="size-3.5" />}
          </button>
        ) : (
          <span className="ml-1.5 size-1.5 rounded-full bg-muted-foreground" aria-hidden="true" />
        )}
        <span className="text-sm text-foreground">{node.name}</span>
      </div>
      {hasChildren && open && (
        <ul className="ml-2 border-l border-border pl-4">
          {node.children?.map((child, index) => <MindMapBranch key={`${child.name}-${index}`} node={child} />)}
        </ul>
      )}
    </li>
  )
}

function isMindMapNode(value: unknown): value is MindMapNode {
  if (typeof value !== "object" || value === null || !("name" in value) || typeof value.name !== "string") return false
  if (!("children" in value) || value.children === undefined) return true
  return Array.isArray(value.children) && value.children.every(isMindMapNode)
}

function DownloadButton({ material, notebookId, label = "Download" }: { material: GeneratedMaterialRead; notebookId: string; label?: string }) {
  const [error, setError] = useState<string | null>(null)
  const [downloading, setDownloading] = useState(false)

  async function download() {
    setDownloading(true)
    setError(null)
    try {
      await downloadGeneratedMaterial(notebookId, material.id, filenameFor(material))
    } catch (downloadError) {
      setError(errorMessage(downloadError, "Couldn't download this material."))
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div>
      <Button type="button" variant="outline" size="sm" disabled={downloading} onClick={download}>
        <Download className="size-3.5" aria-hidden="true" />
        {downloading ? "Downloading…" : label}
      </Button>
      {error && <p className="mt-1.5 text-xs text-destructive" role="alert">{error}</p>}
    </div>
  )
}

function BlobPreview({ material, notebookId }: { material: GeneratedMaterialRead; notebookId: string }) {
  const blobQuery = useQuery({
    queryKey: ["notebooks", notebookId, "studio", material.id, "blob"],
    queryFn: () => getGeneratedMaterialBlob(notebookId, material.id),
    staleTime: Infinity,
  })
  const [objectUrl, setObjectUrl] = useState<string | null>(null)

  useEffect(() => {
    if (!blobQuery.data) return
    const url = URL.createObjectURL(blobQuery.data)
    setObjectUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [blobQuery.data])

  if (blobQuery.isPending) return <p className="text-sm text-muted-foreground" role="status">Loading preview…</p>
  if (blobQuery.isError) return <p className="text-sm text-destructive" role="alert">{errorMessage(blobQuery.error, "Couldn't load the preview.")}</p>
  if (!objectUrl) return null

  return material.artifact_type === "audio" ? (
    <audio controls preload="metadata" src={objectUrl} className="w-full" aria-label={`Play ${material.title}`} />
  ) : (
    <img src={objectUrl} alt={`Generated infographic: ${material.title}`} className="max-h-[36rem] w-full rounded-md object-contain" />
  )
}

function MaterialContent({ material, notebookId }: { material: GeneratedMaterialRead; notebookId: string }) {
  if (material.artifact_type === "report") {
    return material.content ? (
      <div className="min-w-0 font-serif text-sm leading-relaxed text-foreground [&_h1]:mb-2 [&_h1]:mt-4 [&_h1]:text-lg [&_h1]:font-semibold [&_h1]:first:mt-0 [&_h2]:mb-1 [&_h2]:mt-3 [&_h2]:text-base [&_h2]:font-semibold [&_p]:mb-2 [&_p]:last:mb-0 [&_ul]:mb-2 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:mb-2 [&_ol]:list-decimal [&_ol]:pl-5 [&_blockquote]:border-l [&_blockquote]:border-border [&_blockquote]:pl-3 [&_blockquote]:text-muted-foreground [&_table]:mb-2 [&_table]:w-full [&_table]:text-xs [&_th]:border-b [&_th]:border-border [&_th]:py-1 [&_th]:text-left [&_td]:border-b [&_td]:border-border [&_td]:py-1">
        <Markdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>{material.content}</Markdown>
      </div>
    ) : <p className="text-sm text-muted-foreground">This report has no content.</p>
  }

  if (material.artifact_type === "mindmap") {
    if (!material.content) return <p className="text-sm text-muted-foreground">This mind map has no content.</p>
    try {
      const root: unknown = JSON.parse(material.content)
      if (!isMindMapNode(root)) throw new Error("Invalid mind map")
      return <ul><MindMapBranch node={root} /></ul>
    } catch {
      return <p className="text-sm text-destructive" role="alert">This mind map couldn't be displayed because its data is invalid.</p>
    }
  }

  return (
    <div className="flex flex-col gap-3">
      {(material.artifact_type === "audio" || material.artifact_type === "infographic") && <BlobPreview material={material} notebookId={notebookId} />}
      {material.has_download && (
        <DownloadButton
          material={material}
          notebookId={notebookId}
          label={material.artifact_type === "slides" ? "Download slide deck" : material.artifact_type === "data_table" ? "Download CSV" : "Download"}
        />
      )}
    </div>
  )
}

function MaterialRow({ material, notebookId }: { material: GeneratedMaterialRead; notebookId: string }) {
  const [expanded, setExpanded] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const deleteMutation = useDeleteGeneratedMaterial(notebookId)
  const status = STATUS_META[material.status]
  const type = TYPE_META[material.artifact_type]
  const canExpand = material.status === "done"

  return (
    <div>
      <div className="flex items-center gap-2 px-3 py-2.5">
        <button type="button" aria-expanded={canExpand ? expanded : undefined} disabled={!canExpand} onClick={() => setExpanded((value) => !value)} className="flex min-w-0 flex-1 items-center gap-2 rounded text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-default">
          {canExpand ? expanded ? <ChevronDown className="size-4 shrink-0" /> : <ChevronRight className="size-4 shrink-0" /> : <type.icon className="size-4 shrink-0 text-muted-foreground" />}
          <span className="truncate text-sm font-medium text-foreground">{material.title}</span>
          <span className="hidden shrink-0 items-center gap-1 rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground sm:flex"><type.icon className="size-3" aria-hidden="true" />{type.label}</span>
        </button>
        <span className={`flex shrink-0 items-center gap-1 text-xs ${status.className}`}>
          <status.icon className={`size-3.5 ${material.status === "generating" ? "animate-spin motion-reduce:animate-none" : ""}`} aria-hidden="true" />
          {status.label}
        </span>
        {confirming ? (
          <div className="flex shrink-0 items-center gap-1.5">
            <span className="hidden text-xs text-muted-foreground md:inline">Delete?</span>
            <Button variant="destructive" size="xs" disabled={deleteMutation.isPending} onClick={() => deleteMutation.mutate(material.id)}>{deleteMutation.isPending ? "Deleting…" : "Confirm"}</Button>
            <button type="button" className="text-xs text-muted-foreground hover:text-foreground" onClick={() => setConfirming(false)}>Cancel</button>
          </div>
        ) : (
          <button type="button" aria-label={`Delete ${material.title}`} onClick={() => setConfirming(true)} className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"><Trash2 className="size-3.5" aria-hidden="true" /></button>
        )}
      </div>
      {material.status === "failed" && material.error_message && <p className="px-9 pb-2.5 text-xs text-destructive" role="alert">{material.error_message}</p>}
      {deleteMutation.isError && <p className="px-9 pb-2.5 text-xs text-destructive" role="alert">{errorMessage(deleteMutation.error, "Couldn't delete this material.")}</p>}
      {expanded && <div className="border-t border-border px-4 py-4"><MaterialContent material={material} notebookId={notebookId} /></div>}
    </div>
  )
}

export function StudioSection({ notebookId }: { notebookId: string }) {
  const [artifactType, setArtifactType] = useState<ArtifactType>("audio")
  const materialsQuery = useGeneratedMaterials(notebookId)
  const createMutation = useCreateGeneratedMaterial(notebookId)
  const { register, handleSubmit, reset, setValue, watch, formState: { errors } } = useForm<StudioFormValues>({
    defaultValues: { title: "", format: "deep_dive", length: "default", focus: "", prompt: "", orientation: "landscape", detail: "standard", description: "" },
  })
  const reportFormat = watch("format")

  function selectType(type: ArtifactType) {
    setArtifactType(type)
    createMutation.reset()
    const defaults: Record<ArtifactType, Pick<StudioFormValues, "format" | "length">> = {
      audio: { format: "deep_dive", length: "default" }, report: { format: "Briefing Doc", length: "default" },
      slides: { format: "detailed_deck", length: "default" }, infographic: { format: "", length: "default" },
      mindmap: { format: "", length: "default" }, data_table: { format: "", length: "default" },
    }
    setValue("format", defaults[type].format)
    setValue("length", defaults[type].length)
  }

  function onSubmit(values: StudioFormValues) {
    const input: GeneratedMaterialCreate = { artifact_type: artifactType, title: values.title.trim() || undefined }
    if (artifactType === "audio") Object.assign(input, { format: values.format, length: values.length, focus: values.focus.trim() || undefined })
    if (artifactType === "report") Object.assign(input, { format: values.format, prompt: values.format === "Create Your Own" ? values.prompt.trim() || undefined : undefined })
    if (artifactType === "slides") Object.assign(input, { format: values.format, length: values.length })
    if (artifactType === "infographic") Object.assign(input, { orientation: values.orientation, detail: values.detail })
    if (artifactType === "data_table") input.description = values.description.trim()
    createMutation.mutate(input, { onSuccess: () => reset({ ...values, title: "", focus: "", prompt: "", description: "" }) })
  }

  const createError = createMutation.isError
    ? createMutation.error instanceof ApiError && createMutation.error.status === 409
      ? "Studio needs an indexed source before it can generate material. Add a resource and wait for its status to show Indexed, then try again."
      : errorMessage(createMutation.error, "Couldn't start Studio generation.")
    : null

  return (
    <section className="flex flex-col gap-4">
      <form onSubmit={handleSubmit(onSubmit)} className="rounded-md border border-border p-4">
        <div className="mb-4"><h2 className="text-sm font-medium text-foreground">Create in Studio</h2><p className="mt-0.5 text-xs text-muted-foreground">Transform this notebook's indexed resources into a new study format.</p></div>
        <div className="mb-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3" role="group" aria-label="Artifact type">
          {(Object.entries(TYPE_META) as [ArtifactType, (typeof TYPE_META)[ArtifactType]][]).map(([value, meta]) => (
            <button key={value} type="button" aria-pressed={artifactType === value} onClick={() => selectType(value)} className={`rounded-md border p-3 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${artifactType === value ? "border-primary bg-primary/5" : "border-border hover:bg-muted/50"}`}>
              <span className="flex items-center gap-2 text-sm font-medium text-foreground"><meta.icon className="size-4 text-muted-foreground" aria-hidden="true" />{meta.label}</span>
              <span className="mt-1 block text-xs leading-relaxed text-muted-foreground">{meta.description}</span>
            </button>
          ))}
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="flex flex-col gap-1.5"><Label htmlFor="studio-title">Title <span className="font-normal text-muted-foreground">(optional)</span></Label><Input id="studio-title" placeholder="e.g. Final exam review" {...register("title")} /></div>
          {artifactType === "audio" && <><SelectField id="studio-format" label="Format" register={register("format")} options={[["deep_dive", "Deep Dive"], ["brief", "Brief"], ["critique", "Critique"], ["debate", "Debate"]]} /><SelectField id="studio-length" label="Length" register={register("length")} options={[["short", "Short"], ["default", "Default"], ["long", "Long"]]} /><div className="flex flex-col gap-1.5"><Label htmlFor="studio-focus">Focus <span className="font-normal text-muted-foreground">(optional)</span></Label><Input id="studio-focus" placeholder="e.g. Compare the competing theories" {...register("focus")} /></div></>}
          {artifactType === "report" && <><SelectField id="studio-format" label="Format" register={register("format")} options={[["Briefing Doc", "Briefing Doc"], ["Study Guide", "Study Guide"], ["Blog Post", "Blog Post"], ["Create Your Own", "Create Your Own"]]} />{reportFormat === "Create Your Own" && <div className="flex flex-col gap-1.5 sm:col-span-2"><Label htmlFor="studio-prompt">Instructions</Label><Textarea id="studio-prompt" placeholder="Describe the report you want to create" {...register("prompt")} /></div>}</>}
          {artifactType === "slides" && <><SelectField id="studio-format" label="Format" register={register("format")} options={[["detailed_deck", "Detailed Deck"], ["presenter_slides", "Presenter Slides"]]} /><SelectField id="studio-length" label="Length" register={register("length")} options={[["short", "Short"], ["default", "Default"]]} /></>}
          {artifactType === "infographic" && <><SelectField id="studio-orientation" label="Orientation" register={register("orientation")} options={[["landscape", "Landscape"], ["portrait", "Portrait"], ["square", "Square"]]} /><SelectField id="studio-detail" label="Detail" register={register("detail")} options={[["concise", "Concise"], ["standard", "Standard"], ["detailed", "Detailed"]]} /></>}
          {artifactType === "data_table" && <div className="flex flex-col gap-1.5 sm:col-span-2"><Label htmlFor="studio-description">What should the table extract?</Label><Textarea id="studio-description" aria-invalid={Boolean(errors.description)} placeholder="e.g. Extract all dates and events" {...register("description", { validate: (value) => artifactType !== "data_table" || value.trim() !== "" || "Describe what the table should extract." })} />{errors.description && <p className="text-xs text-destructive" role="alert">{errors.description.message}</p>}</div>}
        </div>
        {createError && <p className="mt-3 text-sm text-destructive" role="alert">{createError}</p>}
        <Button type="submit" className="mt-4" disabled={createMutation.isPending}>{createMutation.isPending ? "Starting…" : `Generate ${TYPE_META[artifactType].label.toLowerCase()}`}</Button>
      </form>
      <div>
        <h3 className="mb-2 text-sm font-medium text-foreground">Studio materials</h3>
        {materialsQuery.isPending ? <p className="text-sm text-muted-foreground" role="status">Loading Studio materials…</p> : materialsQuery.isError ? <div className="text-sm text-destructive" role="alert"><p>{errorMessage(materialsQuery.error, "Couldn't load Studio materials.")}</p><button type="button" className="font-medium hover:underline" onClick={() => materialsQuery.refetch()}>Try again</button></div> : materialsQuery.data.items.length === 0 ? <div className="rounded-md border border-border py-10 text-center"><Presentation className="mx-auto size-6 text-muted-foreground" aria-hidden="true" /><p className="mt-2 text-sm text-muted-foreground">No Studio materials generated yet.</p></div> : <div className="rounded-md border border-border">{materialsQuery.data.items.map((material, index) => <div key={material.id}>{index > 0 && <Separator />}<MaterialRow material={material} notebookId={notebookId} /></div>)}</div>}
      </div>
    </section>
  )
}

function SelectField({ id, label, register, options }: { id: string; label: string; register: UseFormRegisterReturn; options: [string, string][] }) {
  return <div className="flex flex-col gap-1.5"><Label htmlFor={id}>{label}</Label><select id={id} className={SELECT_CLASS} {...register}>{options.map(([value, optionLabel]) => <option key={value} value={value}>{optionLabel}</option>)}</select></div>
}
