import { NotebookList } from "@/components/notebook/NotebookList"

export function NotebooksSection() {
  return (
    <section className="flex flex-col gap-3">
      <h2 className="text-sm font-medium text-foreground">Your notebooks</h2>
      <NotebookList />
    </section>
  )
}
