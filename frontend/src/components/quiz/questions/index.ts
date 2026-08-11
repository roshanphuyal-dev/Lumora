import type { ComponentType } from "react"
import type { QuestionType } from "@/lib/quizzes"
import type { QuestionAnswerProps } from "@/components/quiz/questions/types"
import { McqQuestion } from "@/components/quiz/questions/McqQuestion"
import { TrueFalseQuestion } from "@/components/quiz/questions/TrueFalseQuestion"
import { FillBlankQuestion } from "@/components/quiz/questions/FillBlankQuestion"
import { MatchingQuestion } from "@/components/quiz/questions/MatchingQuestion"
import { AssertionReasonQuestion } from "@/components/quiz/questions/AssertionReasonQuestion"
import { ShortAnswerQuestion } from "@/components/quiz/questions/ShortAnswerQuestion"
import { LongAnswerQuestion } from "@/components/quiz/questions/LongAnswerQuestion"
import { CaseStudyQuestion } from "@/components/quiz/questions/CaseStudyQuestion"

export const QUESTION_COMPONENTS: Record<QuestionType, ComponentType<QuestionAnswerProps>> = {
  mcq: McqQuestion,
  true_false: TrueFalseQuestion,
  fill_blank: FillBlankQuestion,
  matching: MatchingQuestion,
  assertion_reason: AssertionReasonQuestion,
  short_answer: ShortAnswerQuestion,
  long_answer: LongAnswerQuestion,
  case_study: CaseStudyQuestion,
}

export * from "@/components/quiz/questions/types"
