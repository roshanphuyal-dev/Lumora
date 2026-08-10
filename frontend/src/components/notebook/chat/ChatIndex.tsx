import { ListTree } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import type { ChatMessageData } from "@/components/notebook/chat/types"

const PREVIEW_LENGTH = 60

interface ChatIndexProps {
  messages: ChatMessageData[]
  onJumpTo: (messageId: string) => void
}

// Indexes by the user's own questions (not every message) -- those are the
// natural landmarks in a long conversation; jumping to a question puts its
// answer immediately below in view too.
export function ChatIndex({ messages, onJumpTo }: ChatIndexProps) {
  const questions = messages.filter((message) => message.role === "user")

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button type="button" variant="outline" size="sm" disabled={questions.length === 0}>
          <ListTree className="size-3.5" aria-hidden="true" />
          Jump to
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="max-h-80 overflow-y-auto">
        {questions.map((question, index) => (
          <DropdownMenuItem key={question.id} onSelect={() => onJumpTo(question.id)}>
            <span className="text-muted-foreground">{index + 1}.</span>{" "}
            {question.content.length > PREVIEW_LENGTH
              ? `${question.content.slice(0, PREVIEW_LENGTH)}…`
              : question.content}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
