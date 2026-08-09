import { NotebookList } from "@/components/notebook/NotebookList"

export function NotebooksListPage() {
  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-8 px-6 py-10">
      <header className="flex flex-col gap-1">
        <h1 className="font-serif text-2xl font-semibold text-foreground">Notebooks</h1>
        <p className="text-sm text-muted-foreground">
          Upload a document from the dashboard to create a new one.
        </p>
      </header>

      <NotebookList />
    </div>
  )
}
