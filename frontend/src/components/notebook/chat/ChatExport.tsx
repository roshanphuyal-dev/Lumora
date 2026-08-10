import { useState } from "react"
import { ChevronDown, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { exportChatToPdf } from "@/lib/chat-export"

interface ChatExportProps {
  title: string
  getAllMessageElements: () => HTMLElement[]
  getSelectedMessageElements: () => HTMLElement[]
  hasSelection: boolean
  hasMessages: boolean
}

// Decoupled from ChatMessage/MessageRenderer on purpose (docs/adr/0009): this
// component only orchestrates *which* rendered DOM nodes to hand to the PDF
// generator, never how a message renders.
export function ChatExport({
  title,
  getAllMessageElements,
  getSelectedMessageElements,
  hasSelection,
  hasMessages,
}: ChatExportProps) {
  const [isExporting, setIsExporting] = useState(false)

  async function handleExport(elements: HTMLElement[]) {
    setIsExporting(true)
    try {
      await exportChatToPdf({ title, messageElements: elements })
    } finally {
      setIsExporting(false)
    }
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button type="button" variant="outline" size="sm" disabled={!hasMessages || isExporting}>
          {isExporting ? (
            <Loader2 className="size-3.5 animate-spin" aria-hidden="true" />
          ) : (
            <ChevronDown className="size-3.5" aria-hidden="true" />
          )}
          Export
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem
          disabled={!hasSelection || isExporting}
          onSelect={() => handleExport(getSelectedMessageElements())}
        >
          Export selected{!hasSelection && " (select messages first)"}
        </DropdownMenuItem>
        <DropdownMenuItem
          disabled={!hasMessages || isExporting}
          onSelect={() => handleExport(getAllMessageElements())}
        >
          Export full conversation
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
