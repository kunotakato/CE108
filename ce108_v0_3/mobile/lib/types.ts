export type Role = "student" | "teacher" | "admin";

export type User = {
  id: number;
  email: string;
  role: Role;
  display_name: string;
  grade?: string | null;
  diagnostic_completed?: number;
};

export type LoginResponse = {
  access_token: string;
  token_type: "bearer";
  user: User;
};

export type DailyPlanItem = {
  id: number;
  plan_id: number;
  question_id: number;
  item_type: string;
  display_order: number;
  reason: string;
  question_text: string;
  question_type: QuestionType;
  importance: number;
  subject_name: string;
  topic_name: string;
  completed: number;
};

export type DailyPlan = {
  id: number;
  plan_date: string;
  recommended_count: number;
  estimated_minutes: number;
  status: string;
  items: DailyPlanItem[];
};

export type QuestionType = "single" | "multiple" | "truefalse" | "numeric";

export type Choice = {
  choice_code: string;
  choice_text: string;
  display_order: number;
};

export type Question = {
  id: number;
  question_type: QuestionType;
  question_text: string;
  choices: Choice[];
  unit?: string | null;
  numeric_tolerance?: number | null;
  subject_name?: string | null;
  topic_name?: string | null;
  difficulty?: number;
  importance?: number;
};

export type AnswerPayload = {
  selected_codes: string[];
  numeric_answer: number | null;
  confidence: string;
  response_time_seconds: number;
  answer_mode: "daily";
};

export type AnswerResult = {
  is_correct: boolean;
  review_date: string;
  question: Question & {
    correct_codes?: string[];
    explanation_short?: string;
    explanation_standard?: string;
    explanation_detailed?: string;
    numeric_answer?: number | null;
    choices?: Array<Choice & { is_correct?: number; explanation?: string | null }>;
  };
};

export type LearningSummary = {
  total: number;
  correct: number;
  accuracy: number;
  avg_seconds: number;
  due_reviews: number;
};

export type MasteryRow = {
  subject_name: string;
  topic_name: string;
  mastery_score: number;
  retention_score: number;
  total_answers: number;
  correct_answers: number;
  last_answered_at?: string | null;
};

export type SessionAnswer = {
  questionId: number;
  subjectName?: string | null;
  topicName?: string | null;
  isCorrect: boolean;
  reviewDate: string;
  seconds: number;
};
